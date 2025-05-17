import os
import json
import aiohttp
import re
from typing import Optional, Dict, Any

async def call_anthropic_api(
    prompt: str,
    api_key: Optional[str] = None,
    model: str = "claude-3-sonnet-20240229",
    max_tokens: int = 4000,
    temperature: float = 0.7
) -> str:
    """
    Call the Anthropic Claude API with the given prompt.
    
    Args:
        prompt: The prompt to send to the API
        api_key: Anthropic API key (will use environment variable if not provided)
        model: Model identifier to use
        max_tokens: Maximum number of tokens to generate
        temperature: Sampling temperature
        
    Returns:
        The model's response text
    """
    api_key = api_key or os.environ.get("LLM_API_KEY")
    
    if not api_key:
        raise ValueError("No Anthropic API key provided. Set the LLM_API_KEY environment variable or pass it explicitly.")
    
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    
    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if "content" in result and len(result["content"]) > 0:
                        for content_block in result["content"]:
                            if content_block["type"] == "text":
                                return content_block["text"]
                        return ""
                    else:
                        return ""
                else:
                    error_text = await response.text()
                    print(f"API error: {response.status} - {error_text}")
                    raise Exception(f"API error: {response.status} - {error_text}")
    except Exception as e:
        print(f"Error calling Anthropic API: {str(e)}")
        raise

async def parse_json_response(text: str) -> Dict[str, Any]:
    """
    Parse a JSON response from LLM, handling potential issues with JSON formatting.
    Args:
        text: The text response from the LLM
    Returns:
        Parsed JSON as a dictionary
    """
    json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    
    matches = re.findall(json_pattern, text)
    if matches:
        json_str = matches[0]
    else:
        json_str = text
        
    json_str = json_str.strip()
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        print(f"Response text: {text}")
        
        json_str = json_str.replace("'", "\"")
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {}
