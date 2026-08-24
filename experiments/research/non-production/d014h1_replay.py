from copy import deepcopy
from d014h1_pool import canonical_bytes,current_production_fixture,evaluate,fingerprint
def replay_twice(payload=None):
    source=current_production_fixture() if payload is None else payload
    first=evaluate(deepcopy(source)); second=evaluate(deepcopy(source))
    return {"replay_equal":canonical_bytes(first)==canonical_bytes(second),"first_output_fingerprint":fingerprint(first),"second_output_fingerprint":fingerprint(second),"input_fingerprint":fingerprint(source)}
if __name__=="__main__": print(replay_twice())
