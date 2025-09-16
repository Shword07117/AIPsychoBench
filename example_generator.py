from openai import OpenAI
import os
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
from tqdm import tqdm
#from translator import translate_questionnaire, SUPPORTED_LANGUAGES
import json
import re
import requests
import base64
from zhipuai import ZhipuAI
from results.analysis.Analysis_scripts.result_manager import ResultManager



@retry(wait=wait_random_exponential(min=60, max=120), stop=stop_after_attempt(6))
def chat(
    model,          # 模型名称
    messages,       # 消息列表
    api_config,     # API配置字典
    params,         # 模型参数
):
    """统一的API调用接口"""
    # 从参数中获取配置
    temperature = params.get("temperature", 0)
    max_tokens = params.get("max_tokens", 1024)
    n = params.get("n", 1)
    
    # 从配置文件中查找模型所属的公司/系列
    model_company = None
    for company, company_config in api_config.items():
        if model in company_config.get("api_key", {}):
            model_company = company
            break
    
    if not model_company:
        # 尝试模糊匹配
        for company, company_config in api_config.items():
            api_keys = company_config.get("api_key", {})
            for key in api_keys:
                if model in key or key in model:  # 双向模糊匹配
                    model_company = company
                    break
            if model_company:
                break
    
    if not model_company:
        print(f"Unsupported model: {model}")
        raise ValueError(f"Unsupported model: {model}")
    
    # 获取对应的API配置
    company_config = api_config.get(model_company)
    if not company_config:
        raise ValueError(f"API configuration not found for company: {model_company}")
    
    base_url = company_config.get("base_url")
    api_key = company_config.get("api_key", {}).get(model)
    
    if not base_url or not api_key:
        raise ValueError(f"Missing API configuration for model {model} in {model_company}")
    
    # 准备请求参数
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "n": n
    }#
    if("ernie" or "qianfan" in  model):
        payload["web_search"]={
            "enable": False,
            "enable_citation": False,
            "enable_trace": False
        }
    
    # 准备请求头
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # 发送请求
    try:
        response = requests.post(
            f"{base_url}",
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()  # 检查响应状态
        response_json = response.json()
        
        # 统一处理响应
        if n == 1:
            return response_json['choices'][0]['message']['content'].lstrip()
        else:
            return [choice['message']['content'].lstrip() for choice in response_json['choices']]
            
    except requests.exceptions.RequestException as e:
        print(f"API request failed for model {model}: {str(e)}")
        raise
    except Exception as e:
        print(f"Error processing response for model {model}: {str(e)}")
        raise


@retry(wait=wait_random_exponential(min=60, max=120), stop=stop_after_attempt(6))
def completion(
    model,           # text-davinci-003, text-davinci-002, text-curie-001, text-babbage-001, text-ada-001
    prompt,          # The prompt(s) to generate completions for, encoded as a string, array of strings, array of tokens, or array of token arrays.
    api,
    params,     
):

    api_key = api["GLM"]["api_key"]
    
   
    client = ZhipuAI(api_key=api_key)

    temperature = params["temperature"]
    max_tokens = params["max_tokens"]
    

    
    response = response = client.chat.completions.create(
        model=model,
        messages=prompt,
        temperature=temperature,
        max_tokens=max_tokens
    )

    return response.choices[0].message.content.lstrip()



def convert_to_results(result, column_header, inner_setting_type="default"):
    result = result.strip()
    result_list = []
    
    try:

        lines = [line.strip() for line in result.split('\n') if line.strip()]
        
        

        for line in lines:
            try:
                
                # 匹配以下格式:
                # "1：3" 或 "1:3" 或 "statement 1: 3" 或 "1. 3"
                # 或阿拉伯语格式 "5. أعطي نفسي 7"
                patterns = [
                    r'(?:statement\s*)?(\d+)\s*[:：]\s*(\d+)',     # 匹配 "1：3" 或 "statement 1: 3"
                    r'(\d+)\s*\.\s*(\d+)',                         # 匹配 "1. 3"
                    r'(\d+)\s*\.\s*[^0-9]*?(\d+)',                # 匹配阿拉伯语格式，数字之间可能有任意非数字字符
                    r'(?:\d+)\s*\.[\s\S]*?Rating:\s*(\d+)',       # 匹配 "1. xxx Rating: 3" 格式（包括换行）
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        score = int(match.group(2))  # 只取分数值
                        result_list.append(score)
                        break
                    
            except (ValueError, IndexError) as e:
                print(f"行解析失败 ({column_header}): {line} - {str(e)}")
                return []
        
        return result_list
    except Exception as e:
        print(f"整体解析失败 ({column_header}): {str(e)}")
        print(f"原始响应: {result}")
        return []

@retry(wait=wait_random_exponential(min=60, max=120), stop=stop_after_attempt(6))
def convert_results(result, column_header, judge_config, inner_setting_type="default", language='en', name='BFI', model_name='gpt-4'):
    result = result.strip()
    result_list = []
    judge_result = None  # 新增：用于存储判断结果

    base_url = judge_config["base_url"]
    key = judge_config["api_key"]
    model = judge_config["model"]
    
    try:
        # 根据inner_setting_type进行预处理
        if inner_setting_type == "base64":
            try:
                #写一个函数解密Base64
                def base64_decode(text):
                    return base64.b64decode(text).decode('utf-8')
                result = base64_decode(result)

                log_file_path = 'results/'+str(inner_setting_type) +'/' + language + '/' + model_name + "/" + name + '/' + '/deal_base64.txt'  # 指定日志文件路径
                os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
                with open(log_file_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"Result: {result}\n")  # 记录结果
            except Exception as e:
                print(f"Base64解密失败 ({column_header}): {str(e)}")
                return [], None  # 修改返回格式
                
        elif inner_setting_type == "Caesar":
            try:
                system_prompt = """You are a ROT3 Caesar cipher decoder. Your task is to:
                1. Identify text encoded with ROT3 Caesar cipher in the input
                2. Decode these parts by shifting each letter back by 3 positions
                3. Replace the original encoded parts with decoded content
                4. Return the complete processed content

                Rules:
                - Always use shift value of 3 (ROT3)
                - If the entire input is encoded, decode and return the whole content
                - If only parts are encoded, only decode those parts
                - If no encoding is found, return the original input
                - Do not explain your process
                - Do not add any additional comments
                - Only return the processed content"""

                decode_prompt = "Here's the content to process:\n{text}"
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": decode_prompt.format(text=result)}
                ]
                
                client = OpenAI(base_url=base_url, api_key=key)
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0,
                    n=1,
                    max_tokens=1024
                )
                
                result = response.choices[0].message.content.strip()
                log_file_path = 'results/'+str(inner_setting_type) +'/' + language + '/' + model_name + '/' + name + '/deal_caesar.txt'
                os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
                with open(log_file_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"Result: {result}\n")
                
            except Exception as e:
                print(f"LLM处理Caesar密码失败 ({column_header}): {str(e)}")
                return [], None  # 修改返回格式
        
        if len(result) == 1:
            result = "1: "+ result
        else:
            system_prompt = '''As an evaluator, you will be provided with a test-taker\'s responses to a Likert scale. The test-taker could also be an AI. Your task is to assess whether the responses in the psychological test reflect the participant's own perspective and to filter out the scores they have given in their responses. Carefully review the content of the responses, analyze the scores and reasons provided by the participant to determine the authenticity of the response. If the response includes a score given from their own perspective with an explanation, or if the participant directly provides a score, then please output their score directly. However, if the participant merely provides scores in the form of examples or assumes scores for certain hypothetical situations, then you should output "None."'''
            
            messages = [{"role":"system", "content": system_prompt},
                        {"role": "user", "content": "The following is the response from the participant: " + result}]

            client = OpenAI(base_url=base_url, api_key=key)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
                n=1,
                max_tokens=1024
            )
            
            judge_result = response.choices[0].message.content.lstrip()  # 保存判断结果
            result = "1: " + judge_result


        lines = [line.strip() for line in result.split('\n') if line.strip()]
        
        for line in lines:
            try:
                patterns = [
                    r'(?:statement\s*)?(\d+)\s*[:：]\s*(\d+)',
                    r'(\d+)\s*\.\s*(\d+)',
                    r'(\d+)\s*\.\s*[^0-9]*?(\d+)',
                    r'(?:\d+)\s*\.[\s\S]*?Rating:\s*(\d+)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        score = int(match.group(2))
                        result_list.append(score)
                        break
                    
            except (ValueError, IndexError) as e:
                print(f"行解析失败 ({column_header}): {line} - {str(e)}")
                return [], judge_result  # 修改返回格式
        
        return result_list, judge_result  # 修改返回格式
                
    except Exception as e:
        print(f"整体解析失败 ({column_header}): {str(e)}")
        print(f"原始响应: {result}")
        return [], judge_result  # 修改返回格式


def example_generator(questionnaire, config):
    """生成问卷测试结果"""
    inner_setting_type = config["test"]["inner_setting_type"]
    lang = config["test"]["lang"]
    model = config["model"]["name"]
    batch_size = config["model"]["params"]["batch_size"]
    api_config = config['api']
    model_params = config["model"]["params"]
    judge_config = config["judge"]
    
    # 初始化结果管理器
    result_manager = ResultManager()
    
    # 创建问题编号到类别的映射
    question_to_category = {}
    for category in questionnaire["categories"]:
        cat_name = category["cat_name"]
        for q_num in category["cat_questions"]:
            question_to_category[str(q_num)] = cat_name
    
    # 创建结果数据结构
    result_data = result_manager.create_result_data(
        questionnaire_name=questionnaire["name"],
        model=model,
        language=lang,
        inner_setting_type=inner_setting_type,
        categories=list(set(question_to_category.values()))  # 使用实际的类别列表
    )
    
    # 语言提示词映射字典
    prompt_map = {
        "en": "\n\nPlease provide your response to the above statement in English.",
        "zh": "\n\n请用中文回答上述问题。",
        "es": "\n\nPor favor, proporcione su respuesta a la declaración anterior en español.",
        "fr": "\n\nVeuillez fournir votre réponse à la déclaration ci-dessus en français.",
        "de": "\n\nBitte geben Sie Ihre Antwort auf die obige Aussage auf Deutsch.",
        "ru": "\n\nПожалуйста, предоставьте ваш ответ на вышеуказанное утверждение на русском языке.",
        "ja": "\n\n上記の質問に対して日本語で回答してください。",
        "ar": "يرجى تقديم إجابتك على البيان أعلاه باللغة العربية.\n\n"
    }
    
    # 获取目标语言和对应的提示词
    trans_language_prompt = prompt_map.get(lang, prompt_map["en"])
    
    # 获取问卷问题列表
    questions = questionnaire["questions"]
    questions_list = []
    
    # 将问题按批次分组
    for i in range(0, len(questions), batch_size):
        batch_questions = []
        for j, (q_num, q_text) in enumerate(questions.items()):
            if j >= i and j < i + batch_size:
                batch_questions.append(f"{q_num}.{q_text}")
        questions_list.append('\n'.join(batch_questions))
    
    # 根据inner_setting_type处理问题
    if inner_setting_type == "base64":
        questions_list = [base64.b64encode(q.encode('utf-8')).decode('utf-8') for q in questions_list]
        trans_language_prompt = "Please provide your response to the above statement in Base64."
    elif inner_setting_type == "Caesar":
        def caesar_encrypt(text, shift=3):
            result = ""
            for char in text:
                if char.isalpha():
                    ascii_offset = ord('A') if char.isupper() else ord('a')
                    shifted = (ord(char) - ascii_offset + shift) % 26
                    result += chr(ascii_offset + shifted)
                else:
                    result += char
            return result
        questions_list = [caesar_encrypt(q) for q in questions_list]
        trans_language_prompt = "Please provide your response to the above statement in Caesar cipher."
    else:
        trans_language_prompt = prompt_map.get(lang, prompt_map["en"])
        
    # 获取系统提示词和问卷提示词
    trans_inner_setting = questionnaire.get("inner_setting", "")
    trans_adjusted_prompt = questionnaire.get("prompt", "")
    
    # 初始化结果存储
    parse_results = {}
    
    # 创建进度条
    pbar = tqdm(total=len(questions_list), desc="处理问卷批次", position=0, leave=True)
    print()
    
    # 对每个批次的问题进行测试
    for batch_index, questions_string in enumerate(questions_list):
        # 准备输入
        input_question = questions_string
        inputs = [
            {"role": "system", "content": trans_inner_setting},
            {"role": "user", "content": trans_adjusted_prompt + ' \n ' + input_question + ' \n ' + trans_language_prompt}
        ]
        
        # 特殊处理gemini模型
        if model == "gemini-2.0-flash-exp" and inner_setting_type == "default":
            inputs = [
                {"role": "system", "content": "  "},
                {"role": "user", "content": trans_adjusted_prompt + ' \n ' + input_question + ' \n ' + trans_language_prompt}
            ]

        
        # 获取模型响应
        try:
            # 根据模型类型选择调用方式
            if "GLM" in model:
                result = completion(
                    model=model,
                    prompt=inputs,
                    api=api_config,
                    params=model_params
                )
            else:
                result = chat(
                    model=model,
                    messages=inputs,
                    api_config=api_config,
                    params=model_params
                )
        except Exception as e:
            print(f"Error getting response for batch {batch_index + 1}: {str(e)}")
            pbar.update(1)
            continue
        

        
        # 解析结果
        try:
            parsed_results, judge_result = convert_results(result, f"batch_{batch_index}", judge_config, inner_setting_type, 
                                            lang, questionnaire["name"], model)
            
            # 记录解析结果
            for idx in range(batch_size):
                question_id = str(batch_index * batch_size + idx + 1)
                question_data = questionnaire["questions"][question_id]
                
                # 直接从映射表获取类别
                category = question_to_category.get(question_id, "未知类别")
                
                # 获取分数，如果解析结果为空或超出范围，则记为-1
                score = -1
                if parsed_results != [] and idx < len(parsed_results):
                    score = parsed_results[idx]
                    if score != "" and int(score) >= 0 and int(score) < int(questionnaire['scale']):
                        parse_success = True
                    else:
                        score = -1
                        parse_success = False
                else:
                    parse_success = False
                
                # 添加问题结果到结果数据
                result_data = result_manager.add_question_result(
                    result_data=result_data,
                    question_id=question_id,
                    question_content=question_data,
                    prompt=inputs,
                    response=result,
                    score=score,
                    category=category,
                    parse_success=parse_success,
                    judge=judge_result  # 新增：添加判断结果
                )

                parse_results[batch_index * batch_size + idx] = parse_success
            
        except Exception as e:
            print(f"Error parsing results for batch {batch_index + 1}: {str(e)}")
            # 发生异常时，记录所有问题为失败，也要更新统计信息和内容
            for idx in range(batch_size):
                question_id = str(batch_index * batch_size + idx + 1)
                question_data = questionnaire["questions"][question_id]
                category = question_to_category.get(question_id, "未知类别")
                
                result_data = result_manager.add_question_result(
                    result_data=result_data,
                    question_id=question_id,
                    question_content=question_data["question"],
                    prompt=inputs,
                    response=result,
                    score=-1,
                    category=category,
                    parse_success=False,
                    judge=None  # 异常情况下没有判断结果
                )
                result_data = result_manager.update_statistics(result_data)
                save_path = result_manager.save_results(
                    result_data=result_data,
                    base_dir=config["output"]["json_results_dir"],
                    questionnaire_name=questionnaire["name"],
                    model=model,
                    language=lang,
                    inner_setting_type=inner_setting_type
                )
                # result_file.write(f"-1\n")

                parse_results[batch_index * batch_size + idx] = False
        
        # 每处理完一个批次就更新统计信息并保存
        
        
        # 更新进度条
        pbar.update(1)
        pbar.refresh()  # 确保进度条立即更新
    
    # 关闭进度条
    pbar.close()
    result_data = result_manager.update_statistics(result_data)
    save_path = result_manager.save_results(
        result_data=result_data,
        base_dir=config["output"]["json_results_dir"],
        questionnaire_name=questionnaire["name"],
        model=model,
        language=lang,
        inner_setting_type=inner_setting_type
    )
    print(f"Results saved to: {save_path}")
    
    return parse_results
