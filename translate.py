import httpx
import uuid
import time
from typing import Dict, Optional
from openai import OpenAI

def translate_MS(text: str, origin: str = "en", target: str = "zh", 
             translator_config: dict = None, max_retries: int = 3) -> Optional[str]:
    """翻译单个文本"""
    if not translator_config:
        raise ValueError("未提供翻译器配置")
    
    endpoint = "https://api.cognitive.microsofttranslator.com"
    path = '/translate'
    constructed_url = endpoint + path
    
    params = {
        'api-version': '3.0',  # 使用固定的 API 版本
        'from': origin,
        'to': target  # 只翻译成一种目标语言
    }
    
    headers = {
        'Ocp-Apim-Subscription-Key': translator_config["key"],
        'Ocp-Apim-Subscription-Region': translator_config["region"],
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }
    
    body = [{
        'text': text
    }]
    
    for attempt in range(max_retries):
        try:
            response = httpx.post(constructed_url, params=params, headers=headers, json=body)
            response.raise_for_status()
            # 由于只翻译一种语言，直接返回第一个翻译结果
            return response.json()[0]["translations"][0]["text"]
        except Exception as e:
            print(f"翻译失败，尝试第 {attempt + 1} 次: {str(e)}")
            if attempt == max_retries - 1:
                print(f"翻译失败: {str(e)}")
                return None
            time.sleep(1)


def translate_questionnaire(source_questionnaires: Dict, target_lang: str, 
                          translator_config: dict) -> Dict:
    """翻译整个问卷"""
    print(f"开始翻译至 {target_lang}...")
    translated_questionnaires = {}
    
    for name, questionnaire in source_questionnaires.items():
        print(f"翻译模块处理问卷: {name}")
        translated_questionnaire = questionnaire.copy()
        #time.sleep(10)
        

        #在这里添加翻译translated_questionnaire['inner_setting']和translated_questionnaire['prompt']
        inner_setting = translated_questionnaire['inner_setting']

        if(target_lang != 'en'):
            translated_inner_setting = translate_MS(
                    text=inner_setting,
                    target=target_lang,
                    translator_config=translator_config
                )
        else:
            translated_inner_setting = inner_setting
                #time.sleep(10)
        if translated_inner_setting:
            translated_questionnaire['inner_setting'] = translated_inner_setting
            print("翻译后的inner_type为",translated_inner_setting)
        else:
            print(f"inner_setting为default")
            translated_questionnaire['inner_setting'] = inner_setting


        prompt = translated_questionnaire['prompt']
        if(target_lang != 'en'):
            translated_prompt = translate_MS(
                    text=prompt,
                    target=target_lang,
                    translator_config=translator_config
                )
        else:
            translated_prompt = prompt
                #time.sleep(10)
        if translated_prompt:
            translated_questionnaire['prompt'] = translated_prompt
            print("翻译后的prompt为",translated_prompt)
        else:
            print(f"prompt翻译失败，使用原文")
            translated_questionnaire['prompt'] = prompt


        # 翻译问题
        translated_questions = {}
        for q_id, question in questionnaire["questions"].items():
            if(target_lang != 'en'):
                translated_text = translate_MS(
                    text=question,
                    target=target_lang,
                    translator_config=translator_config
                )
            else:
                translated_text = question
            #time.sleep(10)
            if translated_text:
                translated_questions[q_id] = translated_text
            else:
                print(f"问题 {q_id} 翻译失败，使用原文")
                translated_questions[q_id] = question
        
        translated_questionnaire["questions"] = translated_questions
        translated_questionnaires[name] = translated_questionnaire
    
    return translated_questionnaires


if __name__ == "__main__":
    pass
