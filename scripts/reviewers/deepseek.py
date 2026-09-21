# -*- coding: utf-8 -*-
"""DeepSeek reviewer transport.

This module only knows how to call DeepSeek and return one JSON decision.
Prompt construction and competition-specific validation stay in review_drafts.py.
"""
from __future__ import print_function

import json
import time

import requests


class ReviewError(RuntimeError):
    pass


class DeepSeekReviewer(object):
    def __init__(self, api_key, model, base_url, timeout=60, retries=2):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.retries = retries

    def review(self, messages):
        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "stream": False,
        }

        last_error = None
        for attempt in range(self.retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code in (429, 500, 502, 503) and attempt < self.retries:
                    time.sleep(2 * (attempt + 1))
                    continue
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return json.loads(content)
            except requests.HTTPError as error:
                body = ""
                if error.response is not None:
                    body = (error.response.text or "").strip()[:300]
                last_error = "%s | %s" % (error, body) if body else error
                if attempt < self.retries:
                    time.sleep(2 * (attempt + 1))
                    continue
            except (requests.RequestException, KeyError, ValueError) as error:
                last_error = "%s: %s" % (type(error).__name__, error)
                if attempt < self.retries:
                    time.sleep(2 * (attempt + 1))
                    continue

        raise ReviewError("DeepSeek 调用失败: %s" % last_error)
