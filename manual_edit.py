from noita_bin_file import NoitaBinFile

FILE = "/minecraft/New folder/entities_41407.bin"


f = NoitaBinFile(FILE)
f.read_file()
f.save_decompressed()
input("decompressed file saved, press enter to recompress")
f = NoitaBinFile(FILE+'.decompressed')
f.read_file()
f.save_compressed()
