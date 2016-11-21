# -*- coding: utf-8 -*-

from sklearn.cross_validation import train_test_split
from sklearn.grid_search import GridSearchCV
from sklearn.metrics import classification_report
from sklearn.svm import SVC
import numpy as np

# サポートベクタマシンで分類を行う際に
# 以下のハイパーパラメータの値やカーネルの種類を決める必要がある
#
# カーネル(linear or RBF, or polynomial )
#　C (linear or RBF, or polynomial)
# gamma (RBF,polynomial)
# degree (polynomial)
# 
# これらの適切な値を決定するためにグリッドサーチを行ってみるスクリプト 
#
# 以下の記事を参考に内容を衛星画像分類向きにすこし改変
# http://qiita.com/sotetsuk/items/16ffd76978085bfd7628
#
## col_num： ##
# 利用するバンド(変数)を明示的に指定する(一部のバンドの情報を抽出する場合)
#
# (1,2,3,4,5) と3つ以上の要素のタプルで指定すると先頭がラベルの列番号でそれ以降は投入するデータの列番号
# Ex. (3,4,5,8,7,12) 3列目をラベルとし4,5,8,7,12列をデータとして投入
#
# または
#
# ラベルの位置とバンド数(変数の数)を指定する(ラベル列の次列から変数列が続いている必要がある)
# (1,5) 2つの要素のタプルで指定すると 先頭がラベルの列番号で 次列から2番目の要素の数だけの列数をデータとして投入
# Ex. (3,5) 3列目をラベルとし次列から5列分を(4-8列目)をデータとして投入
# 
## testsize: トレーニングデータのうち テストデータとして利用するものの割合 (0~1)
## n_fold: k-fold cross validation の 分割数
#
# 入力例(以下の2パターンは同じ意味)
# gsearch("C:\\temp\\test.csv",(2,3,4,5,6,7),0.25,10)
# gsearch("C:\\temp\\test.csv",(2,5),0.25,10)
#
def gsearch (training_data,col_num,testsize,n_fold):

    ## データの読み込み    
    if isinstance(col_num,tuple) is True and len(col_num) > 2:
        # ラベルのカラム番号と各次元の列番号が指定された場合の処理
        # 1列目を0列目と読み替えする
        col_num_1 = tuple(np.array(col_num)-1)
        # CSV ファイルの読み込み
        train_d = np.loadtxt(training_data, usecols = col_num_1,skiprows=1,delimiter=',')
        
    elif isinstance(col_num,tuple) is True and len(col_num) == 2:
        # ラベルのカラム番号と次元数のみ指定された場合の処理
        # 1列目を0列目と読み替えする
        col_num_l = []
        col_num_l.append(col_num[0]-1)
        col_num_b = list(np.array(range(col_num[1]))+col_num[0])
        col_num_1 = col_num_l + col_num_b
        # CSV ファイルの読み込み
        train_d = np.loadtxt(training_data, usecols = col_num_1,skiprows=1,delimiter=',')
        
    else:
        print "error! check your parameters."
    
    # 各バンドのピクセル地が格納された列番号を示すタプルを作成
    band_tuple = tuple(range(1,len(col_num_1)))
    # 教師データのうち各バンドのピクセル値のみの配列データを作成
    train_v = train_d[:,band_tuple]
    # 教師データのうちラベルのみの配列データ作成(train_vと対応させている)
    train_lab = train_d[:,0]
    
    ## トレーニングデータとテストデータに分割．
    X_train, X_test, y_train, y_test = train_test_split(
        train_v, train_lab, test_size=testsize, random_state=0)
    
    ## チューニングパラメータ　## 
    # 必要に応じてレンジを書き換える
    
    tuned_parameters = [{'kernel': ['rbf'], 'gamma': [1e-2, 1e-3, 1e-4],
                         'C': [1, 10, 100, 1000]},
                        {'kernel': ['linear'], 'C': [1, 10, 100, 1000]},
                        {'kernel':['poly'], 'degree' : [1,3], 'gamma': [1e-2, 1e-3, 1e-4], 'C': [1, 10, 100, 1000]}]
    
    scores = ['accuracy', 'precision', 'recall']
    
    for score in scores:
        print '\n' + '='*50
        print score
        print '='*50
    
        clf = GridSearchCV(SVC(C=1), tuned_parameters, cv=n_fold, scoring=score, n_jobs=-1)
        clf.fit(X_train, y_train)
        
        comment1 = u"\nベストパラメータ:\n" # windowsでの表示のため
        print  comment1.encode('shift-jis') # windowsでの表示のため
        #print clf.best_estimator_
        print str(clf.best_estimator_)[4:-1] # コピペ用
        
        comment2 = u"\nトレーニングデータでCVした時の平均スコア:\n"
        print comment2.encode('shift-jis')
        for params, mean_score, all_scores in clf.grid_scores_:
            print "{:.3f} (+/- {:.3f}) for {}".format(mean_score, all_scores.std() / 2, params)

        comment3 = u"\nテストデータでの識別結果:\n"
        print comment3.encode('shift-jis')
        y_true, y_pred = y_test, clf.predict(X_test)
        print classification_report(y_true, y_pred)
    
if __name__ == '__main__':
    print "this is code block"