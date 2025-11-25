import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

# 定位到当前文件所在的目录 (src/agent/prompts)
PROMPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 初始化 Jinja2 环境
env = Environment(
    loader=FileSystemLoader(PROMPT_DIR),
    autoescape=select_autoescape([])
)

class PromptLoader:
    @staticmethod
    def render(template_name: str, **kwargs) -> str:
        """渲染指定模板"""
        template = env.get_template(template_name)
        return template.render(**kwargs)

    @staticmethod
    def split_role_content(full_prompt: str) -> tuple[str, str]:
        """拆分 System 和 User Prompt"""
        system_part = ""
        user_part = ""
        
        if "<system>" in full_prompt and "</system>" in full_prompt:
            start = full_prompt.find("<system>") + 8
            end = full_prompt.find("</system>")
            system_part = full_prompt[start:end].strip()
            
        if "<user>" in full_prompt and "</user>" in full_prompt:
            start = full_prompt.find("<user>") + 6
            end = full_prompt.find("</user>")
            user_part = full_prompt[start:end].strip()
            
        return system_part, user_part