# -*- coding: utf8 -*-
 
### RapidEye Level3A プロダクトをDN→reflectance 変換するスクリプト###

## RapidEye Level3a プロダクト：
## 5000x5000 pixel のgeotiffとして提供され、それぞれにxml形式のメタデータが付与されている
##
# linux/Mac/Windows:
# 
# 1) 任意の場所にrpdeye.py" (このファイル)を置く
# 2) terminal/コマンドプロンプト で　カレントディレクトリを1)の場所に変更
# cd /yourpath
# 3) 以下のコマンドを入力し実行する
# python csv2pmmap.py
# 4) ダイアログボックスが表示されるので変換対象ファイルが格納されているディレクトリを指定する
# OKをクリックすると以下の処理が走ります
# 5) 対象ディレクトリ以下(サブディレクトリを含む)のすべてのプロダクト(geotiff & xml)を探索
# 6) 探索したプロダクトを xmlメタデータの情報を元に DN→reflectance(TOA)変換
# 7) 同ディレクトリに XXXX_stuck_ref.tif  として出力


# モジュールをインポート
import sys
import os
import xml.dom.minidom
import ephem
from osgeo import gdal
from osgeo import gdalconst
import numpy as np
import tkFileDialog
# RapidEye EAI values for the 5 band
eai = {"blue":1977.8, "green":1863.5, "red":1560.4, "rededge":1395.0, "nir":1124.4}

def dn2ref(rootpath):
    
    xmllist = []
    for root, _, files in os.walk(rootpath):
        for file_ in files:
            if file_[-13:] == u'_metadata.xml':
                # 処理するファイルを表示しておく
                print os.path.join(root, file_)
                xmllist.append(os.path.join(root, file_))
    
    if len(xmllist) == 0:
        print "there is no RapidEye product"
        sys.exit(1)
         
    for xmlsrc in xmllist:
            
        # xml データをパース
        dom = xml.dom.minidom.parse(xmlsrc)
        # データツリーから acquisition date ノードを タグネームを使って抽出
        aqdatetag = dom.getElementsByTagName("eop:acquisitionDate")
        # データツリーから acquisition date ノードを タグネームを使って抽出
        elvagltag = dom.getElementsByTagName('opt:illuminationElevationAngle')
        ## solar zenith angle　の算出
        # XMLからelevation angle を抽出
        elvagl = elvagltag[0].firstChild.data
        # 一応floatとしてキャスト
        elv = float(elvagl)
        # solar zenith angle = 90 - sun elevation angle
        szagl = 90 - elv
        ##　earth - sun distance (unit:AU) を算出
        # XMLから acquisition date を抽出
        aqdate = aqdatetag[0].firstChild.data
        # 余分な文字列(TとZ)を置換しyyyy/mm/dd hh:mm:ss.sss 形式に整形
        aqdatetime = aqdate.translate({ord(u'T'): u' ',ord(u'Z'): u''})
        # datetime形式をephem 形式に変換
        sttx = ephem.Date(str(aqdatetime))
        # ephem で earth-sun distance を計算
        sun = ephem.Sun()
        sun.compute(sttx)
        esdist_au = sun.earth_distance
    
        # XMLのpathをディレクトリとファイルメ名に分離
        fpth, fname = os.path.split(xmlsrc)
        # XMLと同じディレクトリにあるTIFF画像のファイル名を定義
        fnras = fpth + "/" + fname[0:-13] + ".tif"
        # gdal で開く
        fras = gdal.Open(fnras,gdalconst.GA_ReadOnly)
        # ファイルがなければ強制的に終了させる
        if fras is None:
            print "error"
            sys.exit(1)
        # ラスタとして出力する際の情報を抽出
        trans = fras.GetGeoTransform()
        #nodata 値の抽出(ここではつかわない)
        #nodatav = fras.GetRasterBand(1).GetNoDataValue()
        # 座標系＆投影法
        proj = fras.GetProjection()
        # XY方向のピクセル数
        cols = fras.RasterXSize
        rows = fras.RasterYSize
        # バンド数(ここではつかわない)
        # bands = fras.RasterCount
    
        # 各バンドを配列として抽出()
        aband1 = fras.GetRasterBand(1).ReadAsArray()
        aband2 = fras.GetRasterBand(2).ReadAsArray()
        aband3 = fras.GetRasterBand(3).ReadAsArray()
        aband4 = fras.GetRasterBand(4).ReadAsArray()
        aband5 = fras.GetRasterBand(5).ReadAsArray()
    
        # radiometric scale factor for radiation(RAD(i)) calculation
        # RAD(i) = DN(i) * RadiometricScaleFactor(i)
        scalef = 0.009999999776482582
        # 各バンドの反射率(TOA)を算出 <TOA:top of atmosphere>
        # RED(i) = RAD(i)*(pi()*power(SunDist,2))/(EAI(i)*cos(SolarZenith))
        # page 12-13 in RE product Specifications
        # http://blackbridge.com/rapideye/upload/RE_Product_Specifications_ENG.pdf
    
        refb1 = aband1*scalef*(np.pi*np.power(esdist_au,2))/(eai["blue"]*np.cos(np.radians(szagl)))
        refb2 = aband2*scalef*(np.pi*np.power(esdist_au,2))/(eai["green"]*np.cos(np.radians(szagl)))
        refb3 = aband3*scalef*(np.pi*np.power(esdist_au,2))/(eai["red"]*np.cos(np.radians(szagl)))
        refb4 = aband4*scalef*(np.pi*np.power(esdist_au,2))/(eai["rededge"]*np.cos(np.radians(szagl)))
        refb5 = aband5*scalef*(np.pi*np.power(esdist_au,2))/(eai["nir"]*np.cos(np.radians(szagl)))
    
        # process: output as raster
        outfile = fnras[0:-4] + "_stack_ref.tif"
        outdriver = gdal.GetDriverByName("GTiff")
        # 5バンド Float32　のラスタデータの型をつくる
        outdata   = outdriver.Create(str(outfile), cols, rows, 5, gdal.GDT_Float32)
        # 各バンドにデータを読み込み
        outdata.GetRasterBand(1).WriteArray(refb1)
        outdata.GetRasterBand(2).WriteArray(refb2)
        outdata.GetRasterBand(3).WriteArray(refb3)
        outdata.GetRasterBand(4).WriteArray(refb4)
        outdata.GetRasterBand(5).WriteArray(refb5)
        outdata.SetGeoTransform(trans)
        outdata.SetProjection(proj)
        # 1処理毎にメッセージ
        print fname[0:-13] + ".tif was successfully converted to reflectance."
    
    print "All processes were successfully finished."
    
if __name__ == '__main__':
    print "this is code block"
    #sham3: ファイルの保存場所の絶対パスを取得
    absp = os.path.dirname(os.path.abspath(sys.argv[0]))
    #sham3: ファイル指定ダイアログボックスの表示
    dirname = tkFileDialog.askdirectory(initialdir=absp, title='Select root directory')
    slashed_dirname = dirname.replace(os.path.sep, '/')
    dn2ref(slashed_dirname + "/")
