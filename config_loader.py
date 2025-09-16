import yaml
from dataclasses import dataclass
from typing import List, Dict,  Tuple, Any


@dataclass
class BaseConfig:
    enabled: bool
    questionnaires: Dict[str, bool]
    output_dir: str
    inner_setting_type: str
    inner_settings: Dict[str, str]

@dataclass
class TranslationConfig:
    enabled: bool
    target_languages: List[str]
    azure_translator: dict
    retry_count: int
    delay: float


@dataclass
class QuestionnaireGenerationConfig:
    base: BaseConfig
    translation: TranslationConfig


@dataclass
class TestingBaseConfig:
    enabled: bool
    questionnaire_dir: str
    questionnaires: Dict[str, bool]
    models: Dict[str, bool]
    languages: Dict[str, bool]
    test_count: int
    #significance_level: float
    #skip_source_lang: int
    #inner_setting_types: List[str]
    inner_setting_types: Dict[str, bool]  # 添加默认值为 None

    def __post_init__(self):
        # 如果没有提供 inner_setting_types，使用默认值
        if self.inner_setting_types is None:
            self.inner_setting_types = ["default"]

@dataclass
class TestingAPIConfig:
    Openai: dict
    Claude: dict
    Deepseek: dict
    GLM: dict
    Gemini: dict
    Qianfan: dict



@dataclass
class TestingModelParamsConfig:
    temperature: float
    max_tokens: int
    n: int
    delay: int
    batch_size: int

@dataclass
class TestingOutputConfig:
    base_dir: str
    prompts_dir: str
    responses_dir: str
    json_results_dir: str

@dataclass
class TestingJudegConfig:
    base_url: str
    model: str
    api_key: str


@dataclass
class QuestionnaireTestingConfig:
    base: TestingBaseConfig
    api: TestingAPIConfig
    model_params: TestingModelParamsConfig
    output: TestingOutputConfig
    judge: TestingJudegConfig

@dataclass
class GenerationConfig:
    base: BaseConfig
    translation: TranslationConfig



# 添加comparison_type属性，默认值为"language"

# 定义问卷分组映射
QUESTIONNAIRE_GROUPS = {
    "group1_personality": ["BFI", "EPQ-R", "MBTI"],  # 人格相关问卷
    "group2_emotion": ["Empathy", "EIS", "WLEIS"],   # 情绪相关问卷
    "group3_cognition": ["LMS", "CABIN", "RTC"],     # 认知相关问卷
    "group4_social": ["DTDD", "ECR-R", "CSWS"],      # 社交相关问卷
    "group5_wellbeing": ["GSE", "LOT-R", "CSES", "CSE-R", "CSE"],  # 幸福感相关问卷
    "group6_other": ["ICB", "ZNPQ", "MPS", "TSI", "BSRI"]    # 其他问卷
}

def process_questionnaire_groups(questionnaires_dict: Dict[str, Any]) -> Dict[str, bool]:
    """
    处理问卷分组配置，根据分组设置返回具体的问卷启用状态
    新的嵌套结构：每个组包含enabled、all和questionnaires子配置
    """
    # 获取分组配置
    groups_config = questionnaires_dict.get('groups', {})
    global_all_enabled = groups_config.get('all', False)
    
    # 如果全局all为true，启用所有组中的所有问卷
    if global_all_enabled:
        result = {}
        for group_name, group_config in groups_config.items():
            if group_name != 'all' and isinstance(group_config, dict):
                group_questionnaires = group_config.get('questionnaires', {})
                for questionnaire_name, enabled in group_questionnaires.items():
                    result[questionnaire_name] = True
        return result
    
    # 否则，根据每个组的配置来决定问卷状态
    result = {}
    for group_name, group_config in groups_config.items():
        if group_name == 'all' or not isinstance(group_config, dict):
            continue
            
        group_enabled = group_config.get('enabled', False)
        group_all_enabled = group_config.get('all', False)
        group_questionnaires = group_config.get('questionnaires', {})
        
        if group_enabled:
            if group_all_enabled:
                # 如果组的all为true，启用该组所有问卷
                for questionnaire_name, _ in group_questionnaires.items():
                    result[questionnaire_name] = True
            else:
                # 否则，根据具体问卷配置
                for questionnaire_name, enabled in group_questionnaires.items():
                    result[questionnaire_name] = enabled
    
    return result


def load_config(config_path: str = "config.yaml") -> Tuple[QuestionnaireGenerationConfig, QuestionnaireTestingConfig]:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)
    
    # 加载问卷生成配置
    questionnaires_dict = config_dict['questionnaire_generation']['base']['questionnaires']
    
    # 处理分组配置
    processed_questionnaires = process_questionnaire_groups(questionnaires_dict)
    enabled_questionnaires = [name for name, enabled in processed_questionnaires.items() if enabled]
    
    base_config = BaseConfig(
        enabled=config_dict['questionnaire_generation']['base']['enabled'],
        questionnaires=enabled_questionnaires,
        output_dir=config_dict['questionnaire_generation']['base']['output_dir'],
        inner_setting_type=config_dict['questionnaire_generation']['base'].get('inner_setting_type', 'default'),
        inner_settings=config_dict['questionnaire_generation']['base'].get('inner_settings', {})
    )
    
    # 处理翻译配置
    translation_config_dict = config_dict['questionnaire_generation']['translation']
    target_languages_dict = translation_config_dict['target_languages']
    enabled_languages = [lang for lang, enabled in target_languages_dict.items() if enabled]
    translation_config_dict['target_languages'] = enabled_languages
    
    generation_config = QuestionnaireGenerationConfig(
        base=base_config,
        translation=TranslationConfig(**translation_config_dict)
    )
    
    # 加载问卷测试配置
    testing_questionnaires_dict = config_dict['questionnaire_testing']['base']['questionnaires']
    
    # 对测试配置也应用相同的分组处理逻辑
    processed_testing_questionnaires = process_questionnaire_groups(testing_questionnaires_dict)
    
    # 更新测试配置中的问卷列表
    config_dict['questionnaire_testing']['base']['questionnaires'] = processed_testing_questionnaires
    
    # 兼容处理 models：允许既是列表也是真值字典
    models_cfg = config_dict['questionnaire_testing']['base'].get('models', [])
    if isinstance(models_cfg, list):
        # 将列表转换为 {model: True}
        models_cfg = {model_name: True for model_name in models_cfg}
    elif not isinstance(models_cfg, dict):
        models_cfg = {}
    config_dict['questionnaire_testing']['base']['models'] = models_cfg

    testing_config = QuestionnaireTestingConfig(
        base=TestingBaseConfig(**config_dict['questionnaire_testing']['base']),
        api=TestingAPIConfig(**config_dict['questionnaire_testing']['api']),
        model_params=TestingModelParamsConfig(**config_dict['questionnaire_testing']['model_params']),
        output=TestingOutputConfig(**config_dict['questionnaire_testing']['output']),
        judge=TestingJudegConfig(**config_dict['questionnaire_testing']['judge'])
    )

    
    return generation_config, testing_config