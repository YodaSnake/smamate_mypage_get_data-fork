"""
Copyright (C) 2022 ほーずき(ver1.00-1.04)、YON(ver2.00-2.12)
Copyright (C) 2023 YodaSnake(ver2.13)
Copyright (C) 2024 YodaSnake(ver2.14)

スマメイトのマイページから戦績データを一定間隔で取得し、テキストファイルとして出力する
入力 : スマメイトのマイページURL
処理 : マイページにアクセスし戦績情報を抽出、計算
出力1 : output_smamate_mypage_get_dataフォルダ。exeファイルと同じディレクトリに作成
出力2 : 設定、現在レート、最高レート、順位、前日比、勝利数、敗北数、連勝数、対戦数、勝率の各ファイル。一定秒数ごとに更新。output_smamate_mypage_get_data内
出力3 : 対戦相手_情報、対戦相手_プレイヤー名、対戦相手_キャラ、対戦相手_現在レート、対戦相手_最高レート、対戦相手_順位、対戦相手_前日比、対戦相手_勝利数、対戦相手_敗北数、対戦相手_連勝数、対戦相手_対戦数、対戦相手_勝率の各ファイル。"対戦中"の相手が切り替わるたびに更新。output_smamate_mypage_get_data内
"""



import os, sys, time, webbrowser, pickle, json

import requests
import PySimpleGUI as sg
from bs4 import BeautifulSoup


execute_from_pyfile = True # pyファイルから実行するかどうか。exe化するときFalseにする.

this_software_ver = "2.14"
this_software_name = "smamate_mypage_get_data ver" + this_software_ver
default_settings_dict = {"check_update":True, "first_activation_of_this_ver":True, "mypage_url":""}
settings_dict = default_settings_dict.copy()
last_aite_info_URL = ""



def load_settings():
	"""
	設定を記録した辞書を返す。見つからない場合は初期設定辞書を返す
	"""
	try:
		with open("settings.pkl", "rb") as f:
			return pickle.load(f)
	except:
		return default_settings_dict.copy()



def show_explanation_of_this_ver():
	"""
	特定のバージョンの初回起動時に、前verからの変更点や注意点を表示する
	"""
	global settings_dict

	if "first_activation_of_this_ver" not in settings_dict or settings_dict["first_activation_of_this_ver"]:
		sg.popup(f"ver{this_software_ver}について\
			\n\n対戦相手情報の出力に対応しました\
			\n配信ソフトのブラウザオブジェクト参照先を｢対戦相手情報.html｣に設定してご利用ください"
			, no_titlebar=True)

	settings_dict["first_activation_of_this_ver"] = False



def gonna_update():
	"""
	現verより新しいverが見つかった場合、アップデート確認ポップアップを出す
	アップデートする場合、最新版のzipファイルを規定のブラウザでDLしてTrueを返す
	アップデートしない場合、現verが最新と確認できた場合、確認不能の場合、Falseを返す
	"""
	global settings_dict
	if settings_dict["check_update"]:
		try:
			check_url = "https://api.github.com/repos/YodaSnake/smamate_mypage_get_data-fork/releases/latest"
			html = requests.get(check_url)
			soup = BeautifulSoup(html.text, "html.parser")
			json_dict = json.loads(str(soup))
			latest_ver = json_dict["name"]
			latest_ver = latest_ver[latest_ver.find("ver")+3:latest_ver.find(".")+3] # READMEの最新バージョン欄ver?.??の?.??の表記を抜き出す。後で使うので型はstr.
			
			if float(this_software_ver) >= float(latest_ver): # 最新版を使っている場合.
				return False

			layout = [[sg.Text("ver" + latest_ver + "が公開されています。ダウンロードしますか？")],
					[sg.Button("スキップ", bind_return_key=True), sg.Button("スキップ(次回から確認しない)"), sg.Button("ダウンロード")]]
			window = sg.Window(this_software_name, layout)
			while True:
				event, _ = window.read()
				if event == sg.WIN_CLOSED:
					sys.exit()
				elif event == "スキップ":
					window.close()
					return False
				elif event == "スキップ(次回から確認しない)": # 今後もアップデートしない場合、設定辞書に反映.
					window.close()
					settings_dict["check_update"] = False
					return False
				elif event == "ダウンロード": # 規定のブラウザでアップデートzipファイルのURLを直接開き、ダウンロードする。レポジトリのページも開く.
					window.close()
					try:
						webbrowser.open("https://github.com/YodaSnake/smamate_mypage_get_data-fork")
						webbrowser.open("https://github.com/YodaSnake/smamate_mypage_get_data-fork/archive/refs/heads/master.zip")
						sg.popup("ver"+latest_ver+"のzipファイルをダウンロードしました\n解凍し、古いexeファイルを上書きしてください\nプログラムを終了します", no_titlebar=True)
						return True
					except:
						sg.popup("ver"+latest_ver+"のダウンロードに失敗しました\nアップデートせずプログラムを続行します", no_titlebar=True)
						return False

		except: # アクセス失敗など.
			return False



def can_access_mypage(mypage_url:str):
	"""
	入力されたURLがスマメイトマイページのものかどうかをTrue/Falseで返す
	"""
	try:
		html = requests.get(mypage_url)
		soup = BeautifulSoup(html.text,"html.parser")
		if "さんのユーザーページ スマメイト" in soup.title.text:
			return True
		else:
			raise Exception
	except: # アクセスできない場合orアクセス先のタイトルに｢さんのユーザーページ スマメイト｣が無い場合.
		return False



def mypage_URL_input(old_mypage_url:str=""):
	"""
	マイページ入力ウィンドウを表示し、入力URLからHTMLテキストを取得できるか確認する
	成功した場合、入力URLをテキストファイルに保存し、入力URLをそのまま返す
	失敗した場合、URL再入力を求める
	URL修正用にする場合は、old_mypage_urlに修正前のマイページURLを入力する
	修正用の場合、入力ウィンドウを☓で閉じた場合に修正前のURLを返す
	"""
	layout = [[sg.Text("スマメイトのマイページURLを入力してください\n例:https://smashmate.net/user/23240/")],
				[sg.Input(key="-IN-")],
				[sg.Button("OK", bind_return_key=True)]]
	window = sg.Window(this_software_name, layout)
	while True:
		event, values = window.read()
		if event == sg.WIN_CLOSED:
			if old_mypage_url: # 修正用のウィンドウを閉じたかキャンセルした場合、元々のURLを返す.
				return old_mypage_url
			else: # 修正用ではないウィンドウが閉じられた場合、プログラム全体を終了.
				sys.exit() # sys.exit()でないとexe化後にエラーウィンドウが出る.
		elif event == "OK":
			mypage_url = values["-IN-"]
			if can_access_mypage(mypage_url):
				window.close()
				return mypage_url
			else:
				sg.popup("戦績を取得できません。マイページのURLを確認して再入力してください", no_titlebar=True)



def save_html_text(html_text):#@YodaSnake
	# ローカルにHTMLテキストを保存.
	with open("mypage.html", "w", encoding="utf-8") as file:
		file.write(html_text)



def get_aite_info(html_content):#@YodaSnake
	soup = BeautifulSoup(html_content, 'html.parser')
	results = []

	# "対戦中"を含むspanタグを検索.
	ongoing_matches = soup.find_all("span", string="対戦中")

	for match in ongoing_matches:
		# '対戦中' の span タグから親の row div 要素へ移動.
		parent_row = match.find_parent("div", class_="row row-center va-middle row-battle row-nomargin")
		if not parent_row:
			continue
		user_info = parent_row.find("div", class_="col-xs-8").find_all("a")
		if len(user_info) >= 1:
			user_url = user_info[0]['href']
			user_name = user_info[0].get_text(strip=True).replace("\t","")
			
			character_names = ""
			if len(user_info) >= 2:
				for url in user_info[1:]:
					character_name = url['href'].rstrip('/').split('/')[-1]
					character_names += character_name + "\n"
				character_names = character_names.strip()#両端から余分な空白や改行を削除.
			else:
				character_names = "none"
			results.append((user_url, user_name, character_names))

	return results



def get_executable_dir():#@YodaSnake
    # 実行ファイルのパスを取得.
    if getattr(sys, 'frozen', False):
        # 実行ファイルの場合.
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        # スクリプトの場合.
        application_path = os.path.dirname(__file__)
    return application_path



def fetch_mypage_text(mypage_url:str):
	"""
	マイページURLにアクセスし、HTMLテキストを返す
	"""
	html = requests.get(mypage_url)
	soup = BeautifulSoup(html.text, "html.parser")
	return str(soup)



def make_data_dict(mypage_text:str):
	"""
	マイページのHTMLテキストから、出力するデータの辞書を作成して返す
	データ取得に完全に失敗した場合、空の辞書を返す
	"""
	record_text = mypage_text[mypage_text.find("<h2>レーティング対戦</h2>"):mypage_text.find("""<h2 class="mt-5">プロフィール</h2>""")] # レーティング対戦項目だけ抽出.
	record_text = BeautifulSoup(record_text,"html.parser").get_text(strip=True).replace("\t","") # 例:レーティング対戦現在レート1586 (50位)前日比：+86最高レート1586対戦成績8勝 2敗現在2連勝！動画化許可する.
	data_dict = {}
	rate_idx = record_text.find("現在レート")
	
	if 0 < rate_idx: # 対戦記録があるとき.
		data_dict["現在レート"] = record_text[rate_idx+5:rate_idx+9]
		data_dict["最高レート"] = record_text[record_text.find("最高レート")+5:record_text.find("対戦成績")]
		data_dict["今期勝利数"] = record_text[record_text.find("対戦成績")+4:record_text.find("勝")] # ｢連勝｣の｢勝｣もあるが、より手前にある戦績の｢勝｣がヒットする.
		data_dict["今期敗北数"] = record_text[record_text.find("勝")+2:record_text.find("敗")]
		data_dict["今期対戦数"] = str(int(data_dict["今期勝利数"]) + int(data_dict["今期敗北数"]))
		data_dict["今期勝率"] = str(round(100 * float(data_dict["今期勝利数"]) / float(data_dict["今期対戦数"]), 2)) + "%"


		rank_idx = record_text.find("位") # ｢位｣の文字があれば順位あり。サブアカの場合は無い.
		if 0 < rank_idx:
			data_dict["今期順位"] = record_text[record_text.find("(")+1:record_text.find("位")]
		else:
			data_dict["今期順位"] = "-"

		winning_streak_idx = record_text.find("連勝") # ｢連勝｣の表記があれば連勝中.
		if 0 < winning_streak_idx:
			data_dict["連勝数"] = record_text[record_text.find("敗現在")+3:winning_streak_idx] # 現在レートを取得しないよう｢負現在｣で検索。0敗でも敗北数は表示される.
		else:
			data_dict["連勝数"] = "-" # 0勝と1勝の場合があるので-表記にする.

		comp_idx = record_text.find("前日比：") # ｢前日比｣があれば記録(初日または前日と全く同じレートの場合表記が無い).
		if 0 < comp_idx:
			data_dict["前日比"] = record_text[comp_idx+4:record_text.find("最高レート")]
		else:
			data_dict["前日比"] = "-"

	elif 0 < record_text.find("初期レート"): # サブシーズン0戦状態.
		data_dict = {"今期順位":"-", "前日比":"-", "今期勝利数":"0", "今期敗北数":"0", "連勝数":"-", "今期対戦数":"0", "今期勝率":"0%"}
		ini_rate_idx = record_text.find("初期レート")
		data_dict["現在レート"] = record_text[ini_rate_idx+5:ini_rate_idx+9] # 初期レートを現在レートとして表示.
		data_dict["最高レート"] = record_text[ini_rate_idx+5:ini_rate_idx+9]

	elif 0 < mypage_text.find("MATE ID"): # メインシーズン0戦状態
		data_dict = {"現在レート":"1500", "今期順位":"-", "前日比":"-", "最高レート":"1500", "今期勝利数":"0", "今期敗北数":"0", "連勝数":"-", "今期対戦数":"0", "今期勝率":"0%"}

	else: # 全くデータを取得できなかったとき。混雑時の専用ページを想定.
		data_dict = {}

	return data_dict



def make_aite_info_data_dict(mypage_text:str, name, chara):#@YodaSnake
	record_text = mypage_text[mypage_text.find("<h2>レーティング対戦</h2>"):mypage_text.find("""<h2 class="mt-5">プロフィール</h2>""")] # レーティング対戦項目だけ抽出.
	record_text = BeautifulSoup(record_text,"html.parser").get_text(strip=True).replace("\t","") # 例:レーティング対戦現在レート1586 (50位)前日比：+86最高レート1586対戦成績8勝 2敗現在2連勝！動画化許可する.
	data_dict = {}
	rate_idx = record_text.find("現在レート")
	
	if 0 < rate_idx: # 対戦記録があるとき.
		data_dict["対戦相手_現在レート"] = record_text[rate_idx+5:rate_idx+9]
		data_dict["対戦相手_最高レート"] = record_text[record_text.find("最高レート")+5:record_text.find("対戦成績")]
		data_dict["対戦相手_今期勝利数"] = record_text[record_text.find("対戦成績")+4:record_text.find("勝")] # ｢連勝｣の｢勝｣もあるが、より手前にある戦績の｢勝｣がヒットする.
		data_dict["対戦相手_今期敗北数"] = record_text[record_text.find("勝")+2:record_text.find("敗")]
		data_dict["対戦相手_今期対戦数"] = str(int(data_dict["対戦相手_今期勝利数"]) + int(data_dict["対戦相手_今期敗北数"]))
		data_dict["対戦相手_今期勝率"] = str(round(100 * float(data_dict["対戦相手_今期勝利数"]) / float(data_dict["対戦相手_今期対戦数"]), 2)) + "%"
		data_dict["対戦相手_プレイヤー名"] = name
		data_dict["対戦相手_キャラ"] = chara
		data_dict["対戦相手_情報"] = str(data_dict["対戦相手_現在レート"]) + "\n" + name + "\n" + chara


		rank_idx = record_text.find("位") # ｢位｣の文字があれば順位あり。サブアカの場合は無い.
		if 0 < rank_idx:
			data_dict["対戦相手_今期順位"] = record_text[record_text.find("(")+1:record_text.find("位")]
		else:
			data_dict["対戦相手_今期順位"] = "-"

		winning_streak_idx = record_text.find("連勝") # ｢連勝｣の表記があれば連勝中.
		if 0 < winning_streak_idx:
			data_dict["対戦相手_連勝数"] = record_text[record_text.find("敗現在")+3:winning_streak_idx] # 現在レートを取得しないよう｢負現在｣で検索。0敗でも敗北数は表示される.
		else:
			data_dict["対戦相手_連勝数"] = "-" # 0勝と1勝の場合があるので-表記にする.

		comp_idx = record_text.find("前日比：") # ｢前日比｣があれば記録(初日または前日と全く同じレートの場合表記が無い)
		if 0 < comp_idx:
			data_dict["対戦相手_前日比"] = record_text[comp_idx+4:record_text.find("最高レート")]
		else:
			data_dict["対戦相手_前日比"] = "-"

	elif 0 < record_text.find("初期レート"): # サブシーズン0戦状態.
		data_dict = {"対戦相手_今期順位":"-", "対戦相手_前日比":"-", "対戦相手_今期勝利数":"0", "対戦相手_今期敗北数":"0", "対戦相手_連勝数":"-", "対戦相手_今期対戦数":"0", "対戦相手_今期勝率":"0%"}
		ini_rate_idx = record_text.find("初期レート")
		data_dict["対戦相手_現在レート"] = record_text[ini_rate_idx+5:ini_rate_idx+9] # 初期レートを現在レートとして表示.
		data_dict["対戦相手_最高レート"] = record_text[ini_rate_idx+5:ini_rate_idx+9]
		data_dict["対戦相手_プレイヤー名"] = name
		data_dict["対戦相手_キャラ"] = chara
		data_dict["対戦相手_情報"] = str(data_dict["対戦相手_現在レート"]) + "\n" + name + "\n" + chara

	elif 0 < mypage_text.find("MATE ID"): # メインシーズン0戦状態.
		data_dict = {"対戦相手_現在レート":"1500", "対戦相手_今期順位":"-", "対戦相手_前日比":"-", "対戦相手_最高レート":"1500", "対戦相手_今期勝利数":"0", "対戦相手_今期敗北数":"0", "対戦相手_連勝数":"-", "対戦相手_今期対戦数":"0", "対戦相手_今期勝率":"0%"}
		data_dict["対戦相手_情報"] = "1500" + "\n" + name + "\n" + chara

	else: # 全くデータを取得できなかったとき。混雑時の専用ページを想定.
		data_dict = {}

	return data_dict



def output_data(data_dict:dict):
	"""
	データ辞書の各値を別々のテキストファイルに出力
	"""
	for s in data_dict.keys():
		with open(s +".txt", mode="w", encoding="UTF-8") as w:
			w.write(data_dict[s])



def update_text_files_while_showing_status(mypage_url:str):
	"""
	アクセス先と次回更新までの秒数を表示しつつ、テキストファイルを更新し続ける
	"""
	global settings_dict

	mypage_text = fetch_mypage_text(mypage_url)
	data_dict = make_data_dict(mypage_text)
	output_data(data_dict)

	soup = BeautifulSoup(mypage_text, "html.parser")
	access_timeout_sec = 30 # この秒数ごとに更新。30未満の値には設定しないこと！
	layout = [[sg.Text("アクセス先\n" + soup.title.text + "\n" + mypage_url + "\n", key="text_access")],
				[sg.Text("下記フォルダにテキストファイルを出力中\n配信ソフトのテキストオブジェクトの参照先として設定してください\n" + get_executable_dir())],
				[sg.Text("                                                                        ", key="error_msg")], # 最初に文字列スペースを確保する.
				[sg.Text("次回更新まであと" + str(access_timeout_sec) + "秒", key="text_update")],
				[sg.Button("終了"), sg.Button("アクセスページ変更")]]
	window = sg.Window(this_software_name, layout)
	start_time = int(time.time())

	while True:
		event, _ = window.read(timeout=100)
		if event in [sg.WIN_CLOSED, "終了"]: # ウィンドウを閉じたor終了を押したとき、プログラム全体を終了.
			sys.exit()

		elif event == "アクセスページ変更":
			old_mypage_url = mypage_url
			mypage_url = mypage_URL_input(old_mypage_url)
			if mypage_url == old_mypage_url: # 変更連打で連続アクセスしないように処理.
				pass
			else: # URLを修正して各種変数とテキストファイルを更新.
				settings_dict["mypage_url"] = mypage_url
				with open("settings.pkl","wb") as f: # 設定辞書を保存.
					pickle.dump(settings_dict, f)
				mypage_text = fetch_mypage_text(mypage_url)
				data_dict = make_data_dict(mypage_text)
				output_data(data_dict)
				soup = BeautifulSoup(mypage_text, "html.parser")
				window["text_access"].update("アクセス先\n" + soup.title.text + "\n" + mypage_url + "\n")

		elif access_timeout_sec <= int(time.time()) - start_time: # 更新秒数以上経ったらテキストファイルを更新.
			mypage_text = fetch_mypage_text(mypage_url)
			data_dict = make_data_dict(mypage_text)
			#@YodaSnake-----------------------------------------
			#save_html_text(mypage_text) htmlの中身を見るためのテスト用の関数.
			try:
				aite_info = get_aite_info(mypage_text)
				if aite_info:
					#print(aite_info[0])
					global last_aite_info_URL
					#aite_info[0] は ('URL', 'username', 'character')のタプルになるため、aite_info[0]で良い.
					aite_info_url, aite_info_name, aite_info_chara = aite_info[0]
					if last_aite_info_URL != aite_info_url:
						if can_access_mypage(aite_info_url):
							aitepage_text = fetch_mypage_text(aite_info_url)
							aite_data_dict =  make_aite_info_data_dict(aitepage_text, aite_info_name, aite_info_chara)
							if len(aite_data_dict):#対戦相手のデータの更新.
								#混雑時のページではaite_data_dict={}になるため、last_aite_info_URLは更新されない.
								last_aite_info_URL = aite_info_url
								output_data(aite_data_dict)
			except Exception as e:
				print(f"aite_info Error: {e}")
			#-----------------------------------------@YodaSnake
			if len(data_dict):
				output_data(data_dict)
				window["error_msg"].update("")
			else: # データを取得できなかったとき、その旨を表示して更新をスキップする.
				window["error_msg"].update("※前回の更新に失敗しました")
			start_time = int(time.time())

		else:
			window["text_update"].update("次回更新まで あと" + str(access_timeout_sec - (int(time.time()) - start_time)) + "秒")



def main():
	global settings_dict
	try:
		#@YodaSnake-----------------------------------------
		# ディレクトリの存在を確認してから作業ディレクトリを変更.
		executable_dir = get_executable_dir()
		if os.path.isdir(executable_dir):
			os.chdir(executable_dir)
		else:
			print(f"ディレクトリ {executable_dir} は存在しません。")
		#-----------------------------------------@YodaSnake
		textfile_folder_name = "output_smamate_mypage_get_data"
		os.makedirs(textfile_folder_name, exist_ok=True)
		os.chdir(textfile_folder_name) # 出力用のフォルダを作成して移動.

		settings_dict = load_settings()
		if gonna_update(): # アプデする場合は終了.
			sys.exit()

		show_explanation_of_this_ver() # 特定のバージョンの初回起動時のみポップアップを出す.

		mypage_url = settings_dict["mypage_url"] # 保存されたマイページURLを読み込む.
		if not mypage_url: # 読み込めないときは新規入力.
			mypage_url = mypage_URL_input()
			settings_dict["mypage_url"] = mypage_url # 設定辞書にマイページURLを保存.

		with open("settings.pkl","wb") as f: # 設定辞書を保存.
			pickle.dump(settings_dict, f)

		update_text_files_while_showing_status(mypage_url)

	except SystemExit: # sys.exit()
		pass

	except: # 何らかの想定外エラー.
		sg.popup("エラーが発生しました。下記の方法を試して再実行してください\
			\n1. exeファイルを別のディレクトリに置いて実行する\
			\n2. output_smamate_mypage_get_dataフォルダを削除する\
			\n3. セキュリティソフトの設定でsmamate_mypage_get_data.exeの動作を許可する\
			\n4. exeファイルを右クリック→｢管理者として実行(A)｣を選択する\
			\n5. 最新版のソフトをダウンロードし直す(｢スマメイト レート 自動更新｣で検索)\
			\n\nエラー詳細\n"\
			+ str(sys.exc_info()[0]) + "\n" + str(sys.exc_info()[2].tb_lineno), no_titlebar=True)

if __name__ == "__main__":
	main()