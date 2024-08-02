from constants import WORLD_PATH
from stream_info import StreamInfoFile
from tools.stats import stream_info_stats


def main():
    current = StreamInfoFile()
    #stream_info_stats(current.items)
    precrash = StreamInfoFile(WORLD_PATH + ".stream_info_precrash")
    added = 0
    matched = 0
    i = 0
    for item in precrash.items:
        if item not in current.items:
            added += 1
            current.items.append(item)
            print("added", item, i, len(precrash.items))
        else:
            matched += 1
            print("skip ", item, i, len(precrash.items))
        i += 1
    print(f"matched {matched}  added {added}")
    current.save("_merged")


if __name__ == '__main__':
    main()
