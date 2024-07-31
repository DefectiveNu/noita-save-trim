def flatten(d):
    d2 = {}
    for k in d:
        if isinstance(d[k], dict):
            d[k] = flatten(d[k])

        try:
            length = len(d[k])
        except:
            length = 999
        if length == 1:
            tmp = list(d[k].items())[0]
            print(f"'{tmp}' {type(tmp)}")
            k2, v = tmp
            d2[f"{k}::{k2}"] = v
        else:
            d2[k] = d[k]
    return d2
