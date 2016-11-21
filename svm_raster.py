# -*- coding: utf8 -*-

##　ラスタデータ(geotiff)を対象とした
## サポートベクタマシン(トレーニングデータ有り)分類 をとりあえず試すためだけのスクリプト
## クロスバリデーションを最後に行う
# 教師データは 以下のような構造の CSV ファイル
# <label,b1_value, b2b_value,... bi_value>
# ラベル(分類カテゴリ値)列の後に各バンドの値が順に入力されている必要がある
# 最初の行に列名を入っていることを想定
# QGISなどからCSVファイルとしてエクスポートしたものをそのまま利用できる
# ex.
# label,b1,b2,...,bi
# 1,158,250,...,125
# 2,95,150,...,60
# 
# モジュールをインポート
import sys
from sklearn import svm
from osgeo import gdal
from osgeo import gdalconst
import numpy as np
import time
from sklearn import cross_validation

# input parameters
# 分類対象ラスタ(フルパス), 教師データCSVファイル(フルパス),CSVファイルのラベルの列番号,クロスバリデーションのfold数,分類結果ラスタ(フルパス)
# 入力例
# gsearch("C:\\temp\\sample.tif","C:\\temp\\training.csv",3,10,"C:\\temp\\svc_out.tif")
#
def svmras(input_raster,training_data,label_column,n_fold,outfile):
    
    # 処理時間計測開始
    start = time.time()
    # GDAL で開く
    fras = gdal.Open(input_raster,gdalconst.GA_ReadOnly)
    
    # 入力画像ファイルの各種情報(ピクセル数 座標値 解像度 座標系など)
    # 分類結果を出力する際に利用する
    trans = fras.GetGeoTransform()
    proj = fras.GetProjection()
    cols = fras.RasterXSize
    rows = fras.RasterYSize
    bands = fras.RasterCount
    
    # すべてのバンドを配列データとして読み込む
    allband = fras.ReadAsArray()
    #  N-d Arrayに変換
    input_array = np.array(allband)
    
    # labelの列番号の修正(0からカウントするため)
    catcolp = label_column - 1
    
    ##　input raster のバンド数にあわせて配列データを加工
    # btuple : 入力ラスタの加工に利用
    # btuple2: トレーニングデータの読み込みに利用
    # 入力ラスタのすべてのバンドを利用すると仮定する
    blist = []
    blist2 = [catcolp]
    for band in range(bands):
        blist.append(input_array[band])
        blist2.append(band + label_column)
    btuple = tuple(blist)
    btuple2 = tuple(blist2)
    
    # [b1],[b2],[b3] というかたちから
    # [b1,b2,b3],[b1,b2,b3] という スタイルに配列を転置
    target_d = np.dstack(btuple)
    # input　raster array の表示(チェック用)
    print "input raster array (first row) is :"
    print target_d[0]
    ## 教師データの読み込み
    # トレーニングデータの読み込み ## 1行目
    train_d = np.loadtxt(training_data, usecols = btuple2,skiprows=1,delimiter=',')
    # 教師データのうち各バンドのピクセル値のみの配列データを作成
    train_v = train_d[:,tuple(range(1,bands+1))]
    # 教師データのうちラベルのみの配列データ作成(train_vと対応させている)
    train_lab = train_d[:,0]
    
    #　教師データの表示(チェック用)
    print "training data (first 3 rows) is :"
    print train_v[:3,]
    print "training data label is :"
    print train_lab
    print "number of training data is " + str(len(train_v))
    print "number of training data label is " + str(len(train_lab))
    
    ## 使用するカーネルやハイパーパラメータの指定
    # estimator = svm.SVC(kernel='poly',degree=3) # polynomial kernel
    # estimator = svm.SVC(kernel='linear')　# linear kernel
    # estimator = svm.SVC(kernel='rbf') # radial basis function kernel
    # scikit-learnの デフォルト値
    # カーネルやハイパーパラメータは gridsearch などを行って決定したものを入力する 
    estimator = svm.SVC(C=1.0, cache_size=200, class_weight=None, coef0=0.0, degree=3,gamma=0.0,
                        kernel='rbf', max_iter=-1, probability=False, random_state=None,shrinking=True,
                        tol=0.001, verbose=False)
    # 教師データをもとにモデルのフィッティング
    estimator.fit(train_v,train_lab)
    ## フィッティング結果を元に予測
    # 1行(row)ずつ処理を行う
    # 最初の行を処理
    prediction = estimator.predict(target_d[0])
    # 2行目から最終行まで繰り返し処理し 処理結果を配列に追加
    
    for i in range(1,len(target_d)):
        prediction =  np.vstack((prediction,estimator.predict(target_d[i])))

    ## 分類結果を出力するファイルの設定

    # ファイル形式をgeotiffに指定
    outdriver = gdal.GetDriverByName("GTiff")
    # # 1バンド 8bit integer のラスタデータの型を作成する
    # cols: x 方向のピクセル数,　row: y 方向のピクセル数
    outdata = outdriver.Create(str(outfile), cols, rows, 1, gdal.GDT_Byte)
    # 分類結果をラスタに書き込む
    outdata.GetRasterBand(1).WriteArray(prediction)
    # Topleftの座標値や解像度などをinputラスタと同じものに指定する
    # top left x, w-e pixel resolution, rotation, top left y, rotation, n-s pixel resolution
    outdata.SetGeoTransform(trans)
    # 投影法をinputラスタと同じものに設定
    outdata.SetProjection(proj)
    
    # Cross-Vaｌidation
    # とりあえず普通の正答率としておく
    scores = cross_validation.cross_val_score(estimator,train_v,train_lab,cv=n_fold,scoring='accuracy')
    print "cross validation score in accuracy: " + str(scores)
    print "accuracy score average: " + str(round(np.mean(scores),5)) + "(+/- " + str(round(np.std(scores),5)) + ")"

    
    # 処理時間を表示
    elapsed_time = time.time() - start
    print("elapsed_time:{0}".format(elapsed_time))
    
    print "successfully finished."
    
    # 処理を終了させる処理が必要
    # 出力ファイルへの Python のアクセスを終了させる
    sys.exit(0)
    
if __name__ == '__main__':
    print "this is code block"