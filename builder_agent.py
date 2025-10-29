import subprocess
import os
from google import genai
from google.genai import types

class BuilderAgent:
    def __init__(self, api_key=None):
        # ✅ Setup API key
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY not provided.")
        self.client = genai.Client(api_key=self.api_key)

    def list_models(self):
        """📋 Show all available Gemini models"""
        print("🔍 Available Gemini models:")
        for m in self.client.models.list():
            print(" -", m.name)

    def build(self, goal):
        """🧩 Generate Python code for a requested goal"""
        prompt = f"Write a complete Python script for: {goal}. Include explanations as comments."
        print("🧠 Generating code from Gemini...")
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            code = getattr(response, "text", "")
        except Exception as e:
            return f"❌ Error generating code: {e}"

        filename = "generated_code.py"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(code)

        success = self.test_and_fix_code(filename)
        if success:
            return f"✅ Code generated successfully!\n📂 File: {filename}"
        else:
            return f"⚠️ Code generated but failed test.\nCheck {filename}"

    def test_and_fix_code(self, filename, max_attempts=3):
        for attempt in range(max_attempts):
            try:
                subprocess.run(["python", filename], timeout=5, check=True)
                print(f"✅ Attempt {attempt+1}: Code ran successfully")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Attempt {attempt+1} failed: {e}")
                with open(filename, "r", encoding="utf-8") as f:
                    code = f.read()
                fixed_code = self.fix_code(code, str(e))
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(fixed_code)
            except subprocess.TimeoutExpired as e:
                print(f"❌ Attempt {attempt+1} timed out: {e}")
        return False

    def fix_code(self, code, error_msg):
        prompt = f"Here is Python code:\n{code}\nIt caused this error:\n{error_msg}\nPlease fix it."
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return getattr(response, "text", code)
        except Exception as e:
            print(f"❌ Error in fix_code: {e}")
            return code

    def deploy_to_render(self, folder="."):
        try:
            subprocess.run(["render", "deploy", folder], check=True)
            return "🚀 Deployed successfully on Render!"
        except Exception as e:
            return f"⚠️ Deploy failed: {e}"

