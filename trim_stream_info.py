from stream_info import StreamInfoFile

f = StreamInfoFile()
print(f"pre-prune  items: {len(f.items): 5d}")
f.trim()
print(f"post-prune items: {len(f.items): 5d}")
f.save()
