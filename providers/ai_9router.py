import requests
import json
from .base_ai import BaseAI

class NineRouterAI(BaseAI):
    def __init__(self, api_key, text_model, image_model, base_url="http://localhost:20128/v1"):
        self.api_key = api_key
        self.text_model = text_model
        self.image_model = image_model
        self.base_url = base_url.rstrip('/')

    def generate_story(self, prompt: str) -> dict:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        system_prompt = (
            "You are a creative writer. Generate a story based on the user's prompt. "
            "Respond ONLY with a JSON object containing these keys: "
            "'title', 'content', 'caption', 'image_prompt'. "
            "The 'image_prompt' should be a descriptive prompt for an AI image generator."
        )
        data = {
            "model": self.text_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "stream": False
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        try:
            result = response.json()
        except Exception:
            raise ValueError(f"AI API returned non-JSON response: {response.text}")
        
        try:
            content_str = result['choices'][0]['message']['content']
            if not content_str:
                raise ValueError("AI returned empty content.")
            return json.loads(content_str)
        except (KeyError, IndexError) as e:
            raise ValueError(f"Unexpected AI response structure: {result}")
        except json.JSONDecodeError:
            # Try to see if the content_str itself is the story (not wrapped in JSON)
            # or if it has some markdown wrapping like ```json ... ```
            import re
            cleaned_content = content_str.strip()
            json_match = re.search(r'```json\s*(.*?)\s*```', cleaned_content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except:
                    pass
            
            raise ValueError(f"Failed to parse AI response as JSON. Raw content: {content_str}")

    def generate_image(self, image_prompt: str) -> str:
        url = f"{self.base_url}/images/generations"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.image_model,
            "prompt": image_prompt,
            "n": 1,
            "size": "auto",
            "quality": "auto",
            "background": "auto",
            "image_detail": "high",
            "output_format": "png"
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            import logging
            logging.error(f"AI Image API Error: {response.status_code} - {response.text}")
        response.raise_for_status()
        result = response.json()
        
        return result['data'][0]['url']
