import os


def token2rel(tokenFileName):
    # 传入形式为'xxxx.tokens',不包括路径
    # Generate .rel files

    numberTokenPhrases("./t2/", "./t3/", tokenFileName)
    sourceFolder = "./t3/"
    name, ext = os.path.splitext(tokenFileName)

    if os.path.exists(sourceFolder + name + '.rel'):
        sentences = []
        sentence = []
        with open(sourceFolder + name + '.rel', 'r', encoding='UTF-8') as f:
            for line in f:
                if line != '\n':
                    sentence.append(line[:-1].split(' '))
                else:
                    if len(sentence) > 0:
                        sentences.append(sentence)
                    sentence = []
            if len(sentence) > 0:
                sentences.append(sentence)

        # print(sentences) [[['2017/1/13', 'CD', 'O', 'O'], ['The', 'DT', 'O', 'O'],

        # Get label sequence
        for sentenceNo, sentence in enumerate(sentences):
            sequence = []
            i = -1
            for token in sentence:
                lastWord = ''
                if token[-1] != 'O':
                    if i > -1:
                        sequence[i]["tokenLen"] = phraselength
                        sequence[i]["lastWord"] = lastWord
                    i += 1
                    sequence.append(
                        {"firstWord": token[0], "tokenNo": token[-1], "tokenType": token[-2], "POS": token[-3],
                         "prediction": '0:ROOT'})
                    phraselength = 1
                elif token[-2][0] == 'I':
                    phraselength += 1
                    lastWord = token[0]
            if len(sequence) > 0:
                sequence[-1]["tokenLen"] = phraselength
                sequence[-1]["lastWord"] = lastWord

            # 每个句子都有一个sequence，是一个列表，默认预测为0:ROOT
            # [{'firstWord': 'The', 'tokenNo': '1', 'tokenType': 'B-Entity', 'POS': 'DT', 'prediction': '0:ROOT', 'tokenLen': 2, 'lastWord': ''},
            # {'firstWord': 'leveraged', 'tokenNo': '2', 'tokenType': 'B-Action', 'POS': 'VBD', 'prediction': '0:ROOT', 'tokenLen': 1, 'lastWord': ''},
            # {'firstWord': 'a', 'tokenNo': '3', 'tokenType': 'B-Entity', 'POS': 'DT', 'prediction': '0:ROOT', 'tokenLen': 22, 'lastWord': ''}]

            # Predict using rules
            prevEntity = 'X'
            prevVerb = 'X'
            prevPrep = 'X'

            for tokenNo, token in enumerate(sequence):

                if token["tokenType"] == 'B-Entity':
                    # 该词的前面是介词
                    # 所有的预测都放在前面一个词上
                    if prevPrep == tokenNo - 1:
                        sequence[tokenNo]["prediction"] = sequence[prevPrep]["tokenNo"] + ':ModObj'
                    # 该词的前面是动词
                    elif prevVerb == tokenNo - 1:
                        sequence[tokenNo]["prediction"] = sequence[prevVerb]["tokenNo"] + ':ActionObj'
                    else:
                        prevEntity = tokenNo

                if token["tokenType"] == 'B-Action':
                    # 该Action由一个词组成且前面有实体
                    if token["tokenLen"] == 1 and prevEntity != 'X':
                        sequence[tokenNo]["prediction"] = sequence[prevEntity]["tokenNo"] + ':SubjAction'
                    # 该Action由be开始，且前面有实体（被动）
                    elif token["firstWord"] == 'be' and prevEntity != 'X':
                        sequence[prevEntity]["prediction"] = token["tokenNo"] + ':ActionObj'
                    # 该Action由is等词开始，而且最后一个词不包含ing，且前面有实体(被动，排除了进行时）
                    elif (token["firstWord"] == 'is' or token["firstWord"] == 'are' or token[
                        "firstWord"] == 'was' or token["firstWord"] == 'were') and token["lastWord"][
                                                                                   -3:] != 'ing' and prevEntity != 'X':
                        sequence[prevEntity]["prediction"] = token["tokenNo"] + ':ActionObj'
                    prevVerb = tokenNo

                elif token["tokenType"] == 'B-Modifier':
                    # 如果修饰词前面有动词
                    if prevVerb != 'X':
                        sequence[tokenNo]["prediction"] = sequence[prevVerb]["tokenNo"] + ':ActionMod'
                    prevPrep = tokenNo

            for token in sequence:
                for token2No, token2 in enumerate(sentence):
                    if token2[-1] == token["tokenNo"]:
                        sentences[sentenceNo][token2No].append(token["prediction"])

        # Write predictions to file
        remove = []
        for sentenceNo, sentence in enumerate(sentences):
            important = False
            for token in sentence:
                if token[3] != 'O' and token[4] == 'O':
                    print(token)
                if token[3] != 'O':
                    important = True
            if not important:
                remove.append(sentenceNo)
        for i in reversed(remove):
            sentences.pop(i)

        # 生成第四步的数据
        wordGroup = []
        for sen in sentences:
            indexList = [[]]  # 每个子列表为一个完整的E/A/M, 加入一个空列表是为了使序号从1开始
            for token in sen:
                if token[2] == 'O':
                    continue
                if token[2][:2] == 'B-':
                    indexList.append([])
                    indexList[-1].append(token[0])
                if token[2][:2] == 'I-':
                    indexList[-1].append(token[0])
            # 再遍历一遍找出subjAction和其对应的单词加入wordGroup
            for token in sen:
                if len(token) == 5 and 'ActionObj' in token[4]:
                    wordGroup.append([])
                    actionIndex = int(token[3])
                    entityIndex = int(token[4].split(':')[0])
                    wordGroup[-1].append(indexList[entityIndex])
                    wordGroup[-1].append(indexList[actionIndex])
        return wordGroup
    else:
        print('relFileNotFound')
        raise FileNotFoundError


def numberTokenPhrases(sourceFolder, targetFolder, tokenFileName):
    lines = ''
    i = 1
    if "tokens" in tokenFileName:
        with open(sourceFolder + tokenFileName, 'r', encoding='UTF-8') as f:
            for line in f:
                if len(line.split(' ')) > 1 and line.split(' ')[2][0] == 'B':
                    string = line[:-1] + ' ' + str(i) + '\n'
                    i += 1
                elif len(line.split(' ')) > 1:
                    string = line[:-1] + ' O\n'
                else:
                    string = line
                    i = 1
                lines += string
        with open(targetFolder + tokenFileName[:-6] + 'rel', 'w', encoding='UTF-8') as f:
            f.write(lines)
    else:
        print('tokenFileNotFound')
        raise FileNotFoundError


if __name__ == "__main__":
    token2rel('The “EyePyramid” Attacks - Securelist.tokens')
