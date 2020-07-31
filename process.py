import os
import io
import pickle
from subprocess import call
from token2rel import token2rel
from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage, PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.layout import LAParams
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.tag import pos_tag
from sklearn.externals import joblib


pdfFolder = "./pdf/"
plaintextFolder = "./plaintext/"
tokenizedFolder = "./tokenized/"
bcFolder = "./bc/"
wsFolder = "./whitespace/"
models_folder = './models/'
t2_folder = './t2/'
t3_folder = './t3/'
results_folder = './results/'
brown_path = 'brown.data'


def pdf2txt(pdf_path, plaintext_path, tokenized_path, ws_path):
    output = io.StringIO()
    with open(pdf_path, 'rb') as f:
        parser = PDFParser(f)
        doc = PDFDocument(parser)
        if not doc.is_extractable:
            raise PDFTextExtractionNotAllowed
        pdfrm = PDFResourceManager()
        lparam = LAParams()
        device = PDFPageAggregator(pdfrm, laparams=lparam)
        interpreter = PDFPageInterpreter(pdfrm, device)

        for page in PDFPage.create_pages(doc):
            interpreter.process_page(page)
            layout = device.get_result()
            for x in layout:
                if hasattr(x, "get_text"):
                    content = x.get_text()
                    output.write(content)
    content = output.getvalue()
    output.close()
    with open(plaintext_path, 'w', encoding='UTF-8') as f:
        for line in sent_tokenize(content):
            f.write(line + '\n\n')
    with open(plaintext_path, 'r', encoding='UTF-8') as f:
        with open(tokenized_path, 'w', encoding='UTF-8') as o, open(ws_path, 'w', encoding='UTF-8') as p:
            for line in f:
                if line == '\n':
                    o.write('\n')
                else:
                    text = word_tokenize(line)
                    tagged = pos_tag(text)
                    str_y = ' '.join(''.join(e) for e in text) + ' '
                    str_x = '\n'.join(' '.join(e) for e in tagged)
                    o.write(str_x + '\n')
                    p.write(str_y)


def brown_clustering(bc_path, tokenized_path):
    with open(tokenized_path, 'r', encoding='UTF-8') as f, \
            open(brown_path, 'r', encoding='UTF-8') as o, open(bc_path, 'w', encoding='UTF-8') as g:
        bc = o.read().split()
        for line_f in f:
            if len(line_f.split()):
                data = line_f.split()[0]
                if data in bc:
                    g.write(line_f.strip() + ' ' + bc[bc.index(data) + 2] + '\n')
                else:
                    g.write(line_f.strip() + ' X\n')
            else:
                g.write('\n')


def transfer(fileName):
    # 需要传入单个pdf文件名，且文件放在pdf文件夹下
    name, ext = os.path.splitext(fileName)
    pdf_path = pdfFolder + fileName
    plaintext_path = plaintextFolder + name + '.txt'
    tokenized_path = tokenizedFolder + name + '.tokens'
    bc_path = bcFolder + name + '.txt'

    ws_path = wsFolder + name + '.txt'

    # 必须先删除现有文件
    if os.path.exists(plaintext_path):
        os.remove(plaintext_path)
    if os.path.exists(tokenized_path):
        os.remove(tokenized_path)
    if os.path.exists(bc_path):
        os.remove(bc_path)
    if os.path.exists(ws_path):
        os.remove(ws_path)
    if os.path.exists(t2_folder + name + '.data'):
        os.remove(t2_folder + name + '.data')
    if os.path.exists(t2_folder + name + '.tokens'):
        os.remove(t2_folder + name + '.tokens')
    if os.path.exists(t3_folder + name + '.rel'):
        os.remove(t3_folder + name + '.rel')

    pdf2txt(pdf_path, plaintext_path, tokenized_path, ws_path)
    brown_clustering(bc_path, tokenized_path)
    command = "crf_test -m " + models_folder + 'model_2_c1e0' + " " + '"' + bc_path + '"' + " >> " + \
              '"' + t2_folder + name + '.data' + '"'
    print('call:' + command)
    call(command, shell=True)

    with open(t2_folder + name + '.data', 'r', encoding='UTF-8') as o, \
            open(t2_folder + name + '.tokens', 'w', encoding='UTF-8') as g:
        for line_o in o:
            sp = line_o.strip().split()
            if len(sp):
                if sp[3] == 'B-Verb':
                    sp[3] = 'B-Action'
                if sp[3] == 'I-Verb':
                    sp[3] = 'I-Action'
                if sp[3] == 'B-Preposition':
                    sp[3] = 'B-Modifier'
                if sp[3] == 'I-Preposition':
                    sp[3] = 'I-Modifier'
                g.write(sp[0] + ' ' + sp[1] + ' ' + sp[3] + '\n')
            else:
                g.write('\n')

    wordGroup = token2rel(name + '.tokens')

    predict_list = []
    for group in wordGroup:
        assert len(group) == 2
        single = ''
        for tokens in group:
            for token in tokens:
                single += token + ' '
        predict_list.append(single)

    cv_3 = joblib.load(models_folder + 'cv_3.pkl')
    cv_4 = joblib.load(models_folder + 'cv_4.pkl')
    cv_5 = joblib.load(models_folder + 'cv_5.pkl')

    predictX_3 = cv_3.transform(predict_list)
    predictX_4 = cv_4.transform(predict_list)
    predictX_5 = cv_5.transform(predict_list)
    clf_C = joblib.load(models_folder + 'SVM_5_C.pkl')
    clf_A = joblib.load(models_folder + 'SVM_5_A.pkl')
    clf_S = joblib.load(models_folder + 'NB_3_S.pkl')
    clf_T = joblib.load(models_folder + 'NB_4_T.pkl')

    predict_C = list(clf_C.predict(predictX_5))
    predict_A = list(clf_A.predict(predictX_5))
    predict_S = list(clf_S.predict(predictX_3))
    predict_T = list(clf_T.predict(predictX_4))

    with open('attrs.pkl', 'rb') as f:
        all_attr = pickle.load(f)
        C_dict = all_attr['C']
        A_dict = all_attr['A']
        S_dict = all_attr['S']
        T_dict = all_attr['T']

    with open(results_folder + name + '.csv', 'w', encoding='utf-8') as f:
        with open(results_folder + name + '.txt', 'w', encoding='utf-8') as g:
            f.write('token,capability,action,strategicObj,tacticalObj\n\n')
            for i, words in enumerate(predict_list):
                g.write('Tokens: ' + words + '\n')
                c = predict_C[i]
                a = predict_A[i]
                s = predict_S[i]
                t = predict_T[i]
                word_list = words.strip().split()
                g.write('Action: ' + A_dict[a] + '\n')
                g.write('Capability: ' + C_dict[c] + '\n')
                g.write('Strategic Objective: ' + S_dict[s] + '\n')
                g.write('Tactical Objective: ' + T_dict[t] + '\n')
                g.write('\n')
                for word in word_list:
                    f.write(word + ',' + C_dict[c] + ',' + A_dict[a] + ',' + S_dict[s] + ',' + T_dict[t] + '\n')
                f.write('\n')


def main():
    for fileName in os.listdir(pdfFolder):
        if fileName[-4:] == '.pdf':
            transfer(fileName)


if __name__ == '__main__':
    main()
