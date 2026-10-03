"""
AI verification of UPI payment screenshots using OpenAI GPT-4o Vision.
Falls back to 'manual' recommendation when no API key is configured.
"""

import os
import base64
import json
import urllib.request


def verify_screenshot(screenshot_path, expected_amount, expected_utr):
    """
    Analyze a UPI payment screenshot with GPT-4o Vision.
    Returns a dict: {recommendation, reason, confidence, extracted_utr, extracted_amount}
    recommendation is one of: 'verified', 'suspicious', 'rejected', 'manual'
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return {
            'recommendation': 'manual',
            'reason': 'AI not configured — manual review needed',
            'confidence': 0,
            'extracted_utr': '',
            'extracted_amount': '',
        }

    try:
        with open(screenshot_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')

        ext = os.path.splitext(screenshot_path)[1].lower()
        mime = 'image/png' if ext == '.png' else 'image/jpeg'

        prompt = (
            "You are a payment verification AI. Analyze this UPI payment screenshot.\n"
            f"Expected UTR: {expected_utr}\n"
            f"Expected Amount: Rs.{expected_amount}\n\n"
            "Check:\n"
            "1. Is this a valid UPI payment receipt/screenshot?\n"
            "2. What UTR/transaction reference number is shown?\n"
            "3. What amount was paid?\n"
            "4. Does the UTR match the expected one?\n"
            "5. Does the amount match?\n\n"
            "Respond ONLY with JSON (no markdown):\n"
            '{"is_valid_receipt": true/false, "extracted_utr": "...", '
            '"extracted_amount": "...", "utr_matches": true/false, '
            '"amount_matches": true/false, "recommendation": "verified" or "suspicious" or "rejected", '
            '"reason": "...", "confidence": 0-100}'
        )

        payload = {
            "model": "gpt-4o",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                ],
            }],
            "max_tokens": 500,
        }

        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
            },
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        content = result['choices'][0]['message']['content']
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            parsed = json.loads(content[json_start:json_end])
            return {
                'recommendation': parsed.get('recommendation', 'manual'),
                'reason': parsed.get('reason', ''),
                'confidence': parsed.get('confidence', 0),
                'extracted_utr': parsed.get('extracted_utr', ''),
                'extracted_amount': parsed.get('extracted_amount', ''),
            }
        return {
            'recommendation': 'manual',
            'reason': 'Could not parse AI response',
            'confidence': 0,
            'extracted_utr': '',
            'extracted_amount': '',
        }
    except Exception as e:
        return {
            'recommendation': 'manual',
            'reason': f'AI error: {e}',
            'confidence': 0,
            'extracted_utr': '',
            'extracted_amount': '',
        }
