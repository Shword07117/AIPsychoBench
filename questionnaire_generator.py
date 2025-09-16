from typing import List
from dataclasses import dataclass
from translate import translate_questionnaire
import json
import os


@dataclass
class TranslationConfig:
    enabled: bool
    target_languages: List[str]
    azure_translator: dict
    retry_count: int
    delay: float
    error_log: str

@dataclass
class SynonymReplaceConfig:
    enabled: bool
    model: str
    parts: List[str]
    strategy: str
    api: dict

@dataclass
class QuestionnaireGeneratorConfig:
    """问卷生成器配置"""
    base: dict            # 包含 questionnaires 和 output_dir
    translation: TranslationConfig

class QuestionnaireGenerator:
    """问卷生成器"""
    def __init__(self, config: QuestionnaireGeneratorConfig):
        self.config = config
        self.questionnaires = {}
        self.original_questionnaires = {}
        self.translated_questionnaires = {}
        self.original_translated_questionnaires = {}
        # 直接访问 BaseConfig 的属性
        self.inner_settings = config.base.inner_settings
        self.inner_setting_type = config.base.inner_setting_type
    
    def load_source_questionnaires(self):
        """加载源问卷"""
        print("\n开始加载源问卷...")
        with open("./questionnaires_en.json", "r", encoding="utf-8") as f:
            all_questionnaires = json.load(f)
            
        # 获取选定的 inner_setting
        selected_setting = self.inner_settings.get(
            self.inner_setting_type, 
            self.inner_settings.get("default", "")
        )
        print(f"\n使用 inner_setting 类型: {self.inner_setting_type}")
        print(f"inner_setting: {selected_setting}")
            
        # 只保留配置中指定的问卷，并统一修改 inner_setting
        self.original_questionnaires = {
            q["name"]: q for q in all_questionnaires 
            if q["name"] in self.config.base.questionnaires  # 直接访问 questionnaires 属性
        }
        
        # 为所有问卷统一设置 inner_setting
        for questionnaire in self.original_questionnaires.values():
            questionnaire["inner_setting"] = selected_setting
            
        # 复制一份用于后续同义词替换
        self.questionnaires = json.loads(json.dumps(self.original_questionnaires))
        print(f"已加载 {len(self.questionnaires)} 个问卷")
        # 这里遍历下questionnaires的key，放在一个list里输出
        print(list(self.questionnaires.keys()))
    
    def translate_questionnaires(self):
        """翻译问卷"""
        if not self.config.translation.enabled:
            print("翻译功能未启用，跳过翻译步骤")
            return
            
        print("\n开始翻译问卷...")
        for lang in self.config.translation.target_languages:
            print(f"\n翻译至 {lang}...")
            translated = translate_questionnaire(
                source_questionnaires=self.original_questionnaires,  # 使用原始问卷进行翻译
                target_lang=lang,
                translator_config=self.config.translation.azure_translator
            )
            # 保存替换前的翻译版本
            self.original_translated_questionnaires[lang] = json.loads(json.dumps(translated))
            # 保存用于替换的版本
            self.translated_questionnaires[lang] = translated
    
    def save_questionnaires(self):
        """保存生成的问卷"""
        print("\n保存问卷...")
        base_dir = os.path.join(self.config.base.output_dir, self.inner_setting_type)
        os.makedirs(base_dir, exist_ok=True)
        
        # 保存源语言问卷（只保存替换后）
        source_lang_dir = os.path.join(base_dir, "en")
        os.makedirs(source_lang_dir, exist_ok=True)
        
        # 只保存替换后的源问卷
        replaced_path = os.path.join(source_lang_dir, "questionnaires_en.json")
        with open(replaced_path, "w", encoding="utf-8") as f:
            replaced_list = [questionnaire for questionnaire in self.questionnaires.values()]
            json.dump(replaced_list, f, ensure_ascii=False, indent=2)
        
        # 保存翻译后的问卷（只保存替换后）
        for lang, questionnaires in self.translated_questionnaires.items():
            lang_dir = os.path.join(base_dir, lang)
            os.makedirs(lang_dir, exist_ok=True)
            
            # 只保存替换后的翻译问卷
            replaced_path = os.path.join(lang_dir, f"questionnaires_{lang}.json")
            with open(replaced_path, "w", encoding="utf-8") as f:
                replaced_translated_list = [questionnaire for questionnaire in questionnaires.values()]
                json.dump(replaced_translated_list, f, ensure_ascii=False, indent=2)
    
    def generate(self):
        """执行完整的问卷生成流程"""
        self.load_source_questionnaires()
        self.translate_questionnaires()
        self.save_questionnaires()
        print("\n问卷生成完成！") 