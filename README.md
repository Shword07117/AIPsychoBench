# AIPsychoBench
## Core Ideas
This paper introduces AIPsychoBench, a specialized benchmark for evaluating the psychological properties of large language models (LLMs). The benchmark uses lightweight role-playing prompts to bypass LLM alignment, thereby increasing the effective response rate and reducing psychological biases. Additionally, AIPsychoBench supports multiple languages, enabling the assessment of differences in LLM psychological characteristics across various linguistic environments.

## Contributions

**Comprehensive Benchmark:** We introduce AIPsychoBench, a benchmark specifically designed for LLM psychometrics. In terms of the volume and diversity of scales, as well as the breadth of languages covered, it is the most comprehensive among similar datasets.

**High Response Rate:** We propose a lightweight role-playing method integrated in AIPsychoBench, without imparting substantial psychometric biases, significantly increasing the effective response rate in LLM psychometry.

**New Measurement Insight:** Through measurements utilizing AIPsychoBench, it has been conclusively demonstrated for the first time that the language environment constitutes a prerequisite that cannot be overlooked in the conduct of LLM psychometry.

## Research Methods
**Scale Collection:** Extensively collected human psychological scales from the internet, books, and academic papers, selecting Likert scales for quantitative evaluation.

**Lightweight Role-Playing Prompt:** Designed lightweight role-playing prompts to enable LLMs to answer questions like human test-takers, thus improving response rates and reducing biases.

**Multilingual Translation:** Translated the lightweight role-playing prompts and original English scales into multiple languages to assess cross-linguistic differences.

**Analysis and Statistics:** Used GPT-4o as an audit model to examine LLM test answers and calculate scale scores.

## Research Conclusions

**Effective Response Rate:** AIPsychoBench significantly increased the effective response rate of LLMs, from a baseline of 70.12% to 90.40%.

**Psychological Bias:** The lightweight role-playing prompts introduced lower psychological biases, averaging 3.3% (positive) and 2.1% (negative).

**Linguistic Impact:** There were significant differences in LLM psychological characteristics across different linguistic environments, with score deviations in some subcategories reaching 5% to 20.2%.

## Future Work
Future research can explore more effective strategies to balance optimizing response rates and minimizing additional biases. Additionally, more precise and comprehensive methods should be developed to measure and interpret biases arising from linguistic variations.

## Discussion
This paper provides support for the research foundation of machine psychology and advances the interpretability of LLMs. Through AIPsychoBench, researchers can gain deeper insights into the psychological properties of LLMs and explore their performance across different linguistic environments.

