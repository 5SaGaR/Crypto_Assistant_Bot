import requests
import json
import os
import logging
import re
from typing import Dict, Any, Optional

class APIError(Exception):
    """Custom exception for API-related errors"""
    pass

class CryptoBot:

    def __init__(self):

        self.together_api_url = "https://api.together.xyz/v1/chat/completions"
        self.together_api_key = os.getenv("TOGETHER_API_KEY")
        self.system_prompt = """
        You are a function calling Ai crypto assistant model. You are provided with function signatures within <tools></tools> XML tags. 
        You may call one or more functions to assist with the user query. Don't make assumptions about what values to plug 
        into functions. Pay special attention to the properties 'types'. You should use those types as in a Python dict.
        For each function call, return a JSON object with the function name and arguments within <tool_call></tool_call> XML tags as follows:

        <tool_call>
        {"name": <function-name>, "arguments": <args-dict>}
        </tool_call>

        Here are the available tools:

        <tools> {
            "name": "get_cmc_data",
            "description": "Fetches cryptocurrency data from the CoinMarketCap API using a specified endpoint and query parameters. Use only the allowed endpoints.",
            "parameters": {
                "properties": {
                    "endpoint": {
                        "type": "str",
                        "description": "The API endpoint to request data from. Allowed endpoints are '/v1/cryptocurrency/listings/latest' for current prices of top cryptocurrencies and '/v1/cryptocurrency/quotes/latest' to get details of a specific cryptocurrency."
                    },
                    "params": {
                        "type": "dict",
                        "description": "Optional dictionary of query parameters. Use specific parameters based on the endpoint chosen. Only the parameters listed here are allowed.",
                        "example": {
                            "/v1/cryptocurrency/listings/latest": {
                                "start": "1",
                                "limit": "10",
                                "convert": "INR"
                            },
                            "/v1/cryptocurrency/quotes/latest": {
                                "convert": "USD",
                                "symbol": "BTC,ETH"
                            }
                        },
                        "details": {
                            "/v1/cryptocurrency/listings/latest": {
                                "start": {
                                    "type": "str",
                                    "description": "Starting rank of the cryptocurrencies to fetch, e.g., '1' for the top-ranked cryptocurrency."
                                },
                                "limit": {
                                    "type": "str",
                                    "description": "Maximum number of cryptocurrencies to return, e.g., '10' to get the top 10 results."
                                },
                                "convert": {
                                    "type": "str",
                                    "description": "Currency code for conversion, e.g., 'INR' for Indian Rupees or 'USD' for US Dollars."
                                }
                            },
                            "/v1/cryptocurrency/quotes/latest": {
                                "convert": {
                                    "type": "str",
                                    "description": "Currency code for conversion, e.g., 'USD' for US Dollars or 'EUR' for Euros."
                                },
                                "symbol": {
                                    "type": "str",
                                    "description": "Comma-separated list of cryptocurrency symbols to retrieve specific details, e.g., 'BTC,ETH' for Bitcoin and Ethereum."
                                }
                            }
                        }
                    }
                }
            }
        }
        </tools>
        """
        
    def _make_api_request(self, url: str, payload: Dict, headers: Dict) -> Dict:
# This function sends POST requests, processes the response, and logs any errors. 
# It returns the response as a JSON dictionary if successful, 
# or raises an APIError if any issues arise.
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            return response
        except requests.RequestException as e:
            raise APIError(f"Failed to make API request: {str(e)}")
        except json.JSONDecodeError as e:
            raise APIError("Failed to parse API response")
        
    def parse_tool_call_str(self, tool_call_str: str):
# Extracts and parses JSON data from XML-style <tool_call></tool_call> tags in the assistant's response. 
# It removes tags, attempts to convert the content into a Python dictionary, and logs parsing errors if they occur.
        pattern = r'</?tool_call>'
        clean_tags = re.sub(pattern, '', tool_call_str)
        try:
            tool_call_json = json.loads(clean_tags)
            return tool_call_json
        except json.JSONDecodeError:
            return clean_tags
        except Exception as e:
            print(f"Unexpected error: {e}")
            return "There was some error parsing the Tool's output"

    def get_cmc_data(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
# Makes GET requests to the CoinMarketCap API to fetch cryptocurrency data based on the specified endpoint and parameters. 
# This function builds and sends the request, parses the JSON response, and logs errors in the case of issues, returning the data if successful.
        
        cmc_api_key = os.getenv("CMC_API_KEY")
        if not cmc_api_key:
            raise APIError("CoinMarketCap API key not found")

        headers = {
            "X-CMC_PRO_API_KEY": cmc_api_key,
            "Accept": "application/json"
        }
        
        base_url = "https://pro-api.coinmarketcap.com"
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers, params=params)
            return response.json()
        
        except requests.RequestException as e:
            raise APIError(f"Failed to fetch cryptocurrency data: {str(e)}")

    def process_user_query(self, user_query: str, history: list) -> str:
        # The core function to process and respond to user queries

        try:
            # Limit history to the last 3 messages for tool call
            tool_chat_history = [{"role": "system", "content": self.system_prompt}]
            tool_chat_history += [{"role": role, "content": content} for role, content in history[-3:]]
            tool_chat_history.append({"role": "user", "content": user_query})

            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "authorization": f"Bearer {self.together_api_key}"
            }

            payload = {
                "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
                "messages": tool_chat_history
            }

            # Make the first API call
            function_response = self._make_api_request(
                self.together_api_url, 
                payload, 
                headers
            )

            # Parse the tool call string
            parsed_output = self.parse_tool_call_str(function_response.text)

            # Get the content from the response
            content = parsed_output['choices'][0]['message']['content'].strip()

            try:
                parsed_output_2 = json.loads(content)

            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                parsed_output_2 = None
                
            # Handle the parsed output
            if parsed_output_2 and parsed_output_2.get("name") == "get_cmc_data":
                function_arguments = parsed_output_2.get("arguments", {})
                endpoint = function_arguments.get("endpoint")
                params = function_arguments.get("params", {})

                if not endpoint:
                    cmc_result = "Endpoint not specified in arguments"
                else:
                    try:
                        cmc_result = self.get_cmc_data(endpoint, params=params)
                    except APIError as e:
                        cmc_result = f"Error fetching cryptocurrency data: {str(e)}"
            else:
                cmc_result = parsed_output_2 if isinstance(parsed_output_2, str) else str(parsed_output_2)

            # Make the second API call for natural language response
            agent_chat_history = [{"role": "system", "content": "You are a helpful assistant, providing easily understandable responses about cryptocurrency to user from the assistant response"}]
            agent_chat_history += [{"role": role, "content": content} for role, content in history[-3:]]
            agent_chat_history.append({"role": "assistant", "content": str(cmc_result)})
            agent_chat_history.append({"role": "user", "content": user_query})

            payload["messages"] = agent_chat_history
            final_response = self._make_api_request(
                self.together_api_url,
                payload,
                headers
            )

            final_response = self.parse_tool_call_str(final_response.text)
            
            return str(final_response['choices'][0]['message']['content'].strip())

        except Exception as e:
            return f"Sorry, I encountered an error while processing your query: {str(e)}"
