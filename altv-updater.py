from enum import Enum
from multiprocessing.dummy import Namespace
import os
import sys
import requests
import argparse
from colorama import Fore, Style, init

args = None
cdnUrls = {
	"modules": {
		"coreclr": {
			"baseUrl": "https://cdn.altv.mp/coreclr-module/{BRANCH}/{PLATFORM}/{FILE}",
			"files": [
				#{"x64_win32": "update.json", "x64_linux": "update.json"},
				{"x64_win32": "AltV.Net.Host.dll", "x64_linux": "AltV.Net.Host.dll"},
				{"x64_win32": "AltV.Net.Host.runtimeconfig.json", "x64_linux": "AltV.Net.Host.runtimeconfig.json"},
				{"x64_win32": "modules/csharp-module.dll", "x64_linux": "modules/libcsharp-module.so"}
			]
		},
		"js": {
			"baseUrl": "https://cdn.altv.mp/js-module/{BRANCH}/{PLATFORM}/{FILE}",
			"files": [
				#{"x64_win32": "update.json", "x64_linux": "update.json"},
				{"x64_win32": "modules/js-module/js-module.dll", "x64_linux": "modules/js-module/libjs-module.so"},
				{"x64_win32": "modules/js-module/libnode.dll", "x64_linux": "modules/js-module/libnode.so.102"}
			]
		},
		"jsbyte": {
			"baseUrl": "https://cdn.altv.mp/js-bytecode-module/{BRANCH}/{PLATFORM}/{FILE}",
			"files": [
				#{"x64_win32": "update.json", "x64_linux": "update.json"},
				{"x64_win32": "modules/js-bytecode-module.dll", "x64_linux": "modules/libjs-bytecode-module.so"}
			]
		}
	},
	"voice_server": {
		"baseUrl": "https://cdn.altv.mp/voice-server/{BRANCH}/{PLATFORM}/{FILE}",
		"files": [
			#{"x64_win32": "update.json", "x64_linux": "update.json"},
			{"x64_win32": "altv-voice-server.exe", "x64_linux": "altv-voice-server"}
		]
	},
	"data": {
		"baseUrl": "https://cdn.altv.mp/data/{BRANCH}/{FILE}",
		"files": [
			#{"x64_win32": "update.json", "x64_linux": "update.json"},
			{"x64_win32": "data/vehmodels.bin", "x64_linux": "data/vehmodels.bin"},
			{"x64_win32": "data/vehmods.bin", "x64_linux": "data/vehmods.bin"},
			{"x64_win32": "data/clothes.bin", "x64_linux": "data/clothes.bin"},
			{"x64_win32": "data/pedmodels.bin", "x64_linux": "data/pedmodels.bin"}
		]
	},
	"server": {
		"baseUrl": "https://cdn.altv.mp/server/{BRANCH}/{PLATFORM}/{FILE}",
		"files": [
			#{"x64_win32": "update.json", "x64_linux": "update.json"},
			{"x64_win32": "altv-server.exe", "x64_linux": "altv-server"}
		]
	},
	"example": {
		"baseUrl": "https://cdn.altv.mp/samples/{FILE}",
		"files": [
			{"x64_win32": "resources.zip", "x64_linux": "resources.zip"}
		]
	},
	"config": {
		"baseUrl": "https://cdn.altv.mp/others/{FILE}",
		"files": [
			{"x64_win32": "server.cfg", "x64_linux": "server.cfg"}
		]
	},
	"others": ["https://cdn.altv.mp/others/start.sh"]
}

class ServerUpdater:
	class Platform(Enum):
		Windows = "x64_win32"
		Linux = "x64_linux"

	class Branch(Enum):
		Dev = "dev"
		RC = "rc"
		Release = "release"

	class Modules(Enum):
		Csharp = "coreclr"
		JavaScript = "js"
		JSByte = "jsbyte"

	settings = Namespace(
		platform = Platform.Windows, #select which platform to download, windows or linux
		branch = Branch.Release, #select which branch to use, choices="dev", "rc", "release"
		modules = [Modules.Csharp, Modules.JavaScript, Modules.JSByte], #download modules for the server, possible values are: coreclr, js, jsbyte
		server = True, #download server binary file
		data = False, #download server datas such as vehmods, vehbins, pedmodels, etc
		example = False, #download example resources to the server
		voice_server = False, #download voice server
		config = False, #download basic config file
		output_dir = "./" #output directory which the script will download the files to (default is the current directory)
	)

	def __init__(self, command_line=True) -> None:
		self.command_line = command_line

		if command_line:
			self.__parse_arguments()

	def __parse_arguments(self):
		parser = argparse.ArgumentParser(description="A small script that helps updating alt:V server")
		parser.add_argument("-p", "--platform", type=str, default="x64_win32", help="select which platform to download, windows or linux", choices=[self.Platform.Windows.value, self.Platform.Linux.value], required=False)
		parser.add_argument("-b", "--branch", type=str, default="release", help="select which branch to use", choices=[self.Branch.Dev.value, self.Branch.RC.value, self.Branch.Release.value], required=False)
		parser.add_argument("-m", "--modules", type=str, nargs="+", help="download modules for the server, possible values are: coreclr, js, jsbyte", choices=[self.Modules.Csharp.value, self.Modules.JavaScript.value, self.Modules.JSByte.value], required=False)
		parser.add_argument("-ss", "--skip_server", action="store_false", help="skip download server binary file", required=False)
		parser.add_argument("-d", "--data", action="store_true", help="download server datas such as vehmods, vehbins, pedmodels, etc)", required=False)
		parser.add_argument("-e", "--example", action="store_true", help="download example resources to the server", required=False)
		parser.add_argument("-vs", "--voice_server", action="store_true", help="download voice server", required=False)
		parser.add_argument("-c", "--config", action="store_true", help="download basic config file", required=False)
		parser.add_argument("--output_dir", type=str, default="./", help="output directory which the script will download the files to (default is the current directory)", required=False)
		
		args = parser.parse_args()

		for key, value in args.__dict__.items():
			setattr(self.settings, key, value)


	def __find_item(self, obj: dict, key: str):
		if key in obj:
			return obj[key]

		for k, v in obj.items():
			if isinstance(v, dict):
				return self.__find_item(v, key)

		return None

	def __get_options(self):
		options = self.settings.__dict__
		return_data = []

		for key, value in options.items():
			if not value:
				continue

			if type(value) is list:
				for v in value:
					if issubclass(type(v), Enum):
						v = v.value

					data = self.__find_item(cdnUrls, v)
					if data:
						return_data.append(data)

				continue

			if key in cdnUrls:
				return_data.append(cdnUrls[key])
						
		return return_data

	def __download_file(self, url: str, filename: str, callback):
		
		output_path = os.path.abspath(os.path.join(self.settings.output_dir, filename))
		os.makedirs(os.path.dirname(output_path), exist_ok=True)

		response = requests.get(url, stream=True)
		content_length = response.headers.get('content-length')

		# skip files which is not found
		if response.status_code == 404:
			return

		if content_length:
			content_length = int(content_length)

		with open(output_path, "wb") as f:

			if not content_length: # no content length header
				f.write(response.content)

				if callback:
					callback(filename, 1, 1)
			else:
				downloaded = 0
				for data in response.iter_content(chunk_size=4096):
					downloaded += len(data)
					f.write(data)

					if callback:
						callback(filename, downloaded, content_length)

	def get_files(self):
		return_data = []

		for option in self.__get_options():
			for dfile in option["files"]:
				filename = dfile[self.settings.platform]
				url = option["baseUrl"] \
					.replace("{BRANCH}", self.settings.branch) \
					.replace("{PLATFORM}", self.settings.platform) \
					.replace("{FILE}", filename)

				return_data.append({"url": url, "filename": filename})

		return_data.sort(key=lambda x: (-x["filename"].count('/'), x["filename"]))
		return return_data

	def update(self, callback):
		
		for d_file in self.get_files():
			self.__download_file(d_file["url"], d_file["filename"], callback)

class Utils:
	__progress_bar_width = 50
	__progress_bar_name_width = 32

	def progress_bar(current_length, max_length, name = ""):
		percentage = int(current_length / max_length * 100)
		done = int(Utils.__progress_bar_width * current_length / max_length)
	
		print(f"%s 0%%[{Fore.GREEN}%s{Style.RESET_ALL}%s%s]100%% %d/%d bytes" % (name[:Utils.__progress_bar_name_width].rjust(Utils.__progress_bar_name_width), '=' * done, percentage, ' ' * (Utils.__progress_bar_width - done), current_length, max_length ), end="\r", flush=True)

	#Source: https://stackoverflow.com/a/3041990
	def query_yes_no(question, default="yes"):
		"""Ask a yes/no question via raw_input() and return their answer.
		"question" is a string that is presented to the user.
		"default" is the presumed answer if the user just hits <Enter>.
				It must be "yes" (the default), "no" or None (meaning
				an answer is required of the user).
		The "answer" return value is True for "yes" or False for "no".
		"""
		valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
		if default is None:
			prompt = " [y/n] "
		elif default == "yes":
			prompt = " [Y/n] "
		elif default == "no":
			prompt = " [y/N] "
		else:
			raise ValueError("invalid default answer: '%s'" % default)

		while True:
			sys.stdout.write(question + prompt)
			choice = input().lower()
			if default is not None and choice == "":
				return valid[default]
			elif choice in valid:
				return valid[choice]
			else:
				sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")

last_file = ""
def update_callback(filename, dlnow, dltotal):
	global last_file

	if last_file != filename:
		last_file = filename
		print()

	Utils.progress_bar(dlnow, dltotal, filename)

def main():

	init(convert=True)
	updater = ServerUpdater()

	print("[======== alt:V Updater ========]")
	print(f"Branch: {Fore.GREEN}{updater.settings.branch}{Style.RESET_ALL}")
	print(f"Platform: {Fore.GREEN}{updater.settings.platform}{Style.RESET_ALL}")
	print()
	print(f"The following files will be downloaded into {Fore.GREEN}{os.path.abspath(updater.settings.output_dir)}{Style.RESET_ALL}:")
	
	for x in updater.get_files():
		print(f"{Fore.GREEN}{x['filename']}{Style.RESET_ALL}")

	print()

	answer = Utils.query_yes_no("Do you want to process and download the files listed above?")
	if answer:
		updater.update(update_callback)

		print()
		print()

if __name__ == "__main__":
	main()