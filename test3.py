import spacy
nlp = spacy.load('zh_core_web_sm')
doc = nlp("这是一个测试文本。")
print([token.text for token in doc])
