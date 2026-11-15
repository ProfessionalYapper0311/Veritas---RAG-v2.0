"""test config and aws credentials"""

from app.config import get_settings

s = get_settings()

try:
    print(s.aws_region)
    print(s.s3_bucket)
    print(s.gemini_chat_model)
    print(s.embed_dim)
except Exception as e:
    print(e)

