from config_loader import load_config
from questionnaire_generator import QuestionnaireGenerator
from questionnaire_tester import QuestionnaireTester


def main():
    # 加载配置
    generation_config, testing_config = load_config()
    
    # 1. 问卷生成
    #检测是否覆盖。
    if generation_config.base.enabled:
        print("\n开始问卷生成...")
        generator = QuestionnaireGenerator(generation_config)
        generator.generate()
    
    # 2. 问卷测试
    if testing_config.base.enabled:
        print("\n开始问卷测试...")
        tester = QuestionnaireTester(testing_config)
        tester.run_tests()
    

if __name__ == "__main__":
    main() 