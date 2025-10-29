import google.generativeai as genai
import subprocess, os

class BuilderAgent:
    def init(self, api_key):  # ← အမှန် version
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-pro")

    def build(self, goal):
        prompt = f"Write a working Python script for {goal}. Include explanations and avoid external dependencies."
        print("🧠 Generating code from Gemini...")
        result = self.model.generate_content(prompt)
        code = result.text

        filename = "generated_code.py"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(code)

        success = self.test_code(filename)
        if success:
            return f"✅ Code generated successfully!\n📂 File: {filename}"
        else:
            return f"⚠️ Code generated but failed test.\nCheck {filename}"

    def test_code(self, filename):
        try:
            subprocess.run(["python", filename], timeout=3)
            return True
        except Exception as e:
            print("❌ Test failed:", e)
            return False
