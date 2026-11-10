"""Small tree beam search scored by whole-query first stops, not state impurity."""
from dataclasses import dataclass
import math
import numpy as np

from offline_common import DESIGN, digest


@dataclass
class Data:
    rows: list
    names: list
    kinds: dict
    checkpoints: list
    values: np.ndarray
    valid_bits: np.ndarray
    activation: np.ndarray
    reuse: np.ndarray
    deficit: np.ndarray
    invalid: np.ndarray
    group_index: np.ndarray
    filter_index: np.ndarray


def prepare(rows, condition, profile, base_names, training_groups):
    from contract import CONDITIONS, EXTRA
    spec = CONDITIONS[condition]
    family = 'local' if spec['local_filter'] else 'base'
    selected = sorted((q for q in rows if q['group'] in set(training_groups)),
                      key=lambda q: (q['group'], q['stratum']))
    groups = sorted(set(training_groups))
    if len(selected) != 3*len(groups) or {q['group'] for q in selected} != set(groups):
        raise ValueError('Three filters per fitting group required')
    if any({q['stratum'] for q in selected if q['group']==g} != {'unfiltered','votes32','votes108'} for g in groups):
        raise ValueError('Fitting filter inventory differs')
    names = sorted(set(base_names) | (set(EXTRA) if spec['local_filter'] else set()))
    kinds = {n: profile.runtime_features[n].kind for n in names}
    cps = spec['checkpoints']
    n, width = len(selected), len(cps)
    values = np.full((n, width, len(names)), np.nan)
    valid = np.zeros(n, dtype=np.uint16)
    a = np.zeros((n, width+1)); w = a.copy(); loss = a.copy()
    invalid = np.ones((n, width+1), dtype=bool)
    for i, q in enumerate(selected):
        states = {s['checkpoint_index']: s['features'] for s in q[family+'_states']}
        labels = q['labels'][family]
        for j, cp in enumerate(cps):
            if cp not in states:
                if str(cp) in labels: raise ValueError('Label without state')
                continue
            if str(cp) not in labels:
                raise ValueError('Unknown actual stop: acquisition required')
            f = states[cp]
            if any(f.get(name) is None for name in names):
                raise ValueError('Qualified feature pool is incomplete; no missing-value interpolation')
            for name in names:
                if kinds[name] == 'int' and abs(f[name]) > 2**53:
                    raise ValueError('Integer not exactly represented in fitting matrix')
            values[i, j] = [f[name] for name in names]
            valid[i] |= np.uint16(1 << j)
            label = labels[str(cp)]
            a[i,j], w[i,j] = label['activation_ms_saved'], label['reuse_ms_saved']
            loss[i,j] = max(0., q['native_recall']-label['recall'])
            invalid[i,j] = not (label['valid'] and label['returned_count'] == 10)
        c = q['continue_costs'][family]
        a[i,-1], w[i,-1] = c['activation_ms_saved'], c['reuse_ms_saved']
        loss[i,-1], invalid[i,-1] = 0., False
    return Data(selected, names, kinds, cps, values, valid, a, w, loss, invalid,
                np.asarray([groups.index(q['group']) for q in selected]),
                np.asarray([('unfiltered','votes32','votes108').index(q['stratum']) for q in selected]))


def first_indices(masks, width):
    table = np.full(1 << width, width, dtype=np.uint8)
    for mask in range(1, len(table)):
        table[mask] = (mask & -mask).bit_length()-1
    return table[np.asarray(masks, dtype=np.uint16)]


def scores(data, masks, risk):
    masks = np.atleast_2d(masks)
    if np.any(masks & (~data.valid_bits[None,:])):
        raise ValueError('Candidate requests an unmeasured state')
    idx = first_indices(masks, len(data.checkpoints))
    q = np.arange(len(data.rows))[None,:]
    utility = np.minimum(data.activation[q,idx].mean(axis=1), data.reuse[q,idx].mean(axis=1))
    deficits = data.deficit[q,idx]
    worst = np.maximum.reduce([deficits.mean(axis=1), *[
        deficits[:,data.filter_index == f].mean(axis=1) for f in range(3)]])
    result = utility-risk*worst
    result[data.invalid[q,idx].any(axis=1)] = -1e100
    return result


def atoms_for(data):
    atoms, high_masks = [], []
    width = len(data.checkpoints)
    powers = (1 << np.arange(width)).astype(np.uint16)
    for col, name in enumerate(data.names):
        v = data.values[:,:,col]
        observed = v[np.isfinite(v)]
        cuts = [.5] if data.kinds[name] == 'bool' else np.unique(np.quantile(observed, DESIGN['threshold_quantiles']))
        cuts = sorted(set(math.ceil(float(t)) if data.kinds[name] == 'int' else float(t) for t in cuts))
        for cut in cuts:
            h = np.bitwise_or.reduce(np.where(v >= cut, powers, 0).astype(np.uint16), axis=1)
            h &= data.valid_bits
            if not np.any(h) or np.array_equal(h, data.valid_bits):
                continue
            atoms.append((name, data.kinds[name], cut)); high_masks.append(h)
    return atoms, np.asarray(high_masks, dtype=np.uint16).reshape((-1,len(data.rows)))


def nodes(tree):
    return 0 if isinstance(tree, bool) else 1+nodes(tree[1])+nodes(tree[2])


def replace(tree, path, subtree):
    if not path: return subtree
    atom, high, low = tree
    return (atom, replace(high,path[1:],subtree),low) if path[0] == 1 else (atom,high,replace(low,path[1:],subtree))


def leaves(tree, high_masks, valid_bits, path=(), reach=None):
    if reach is None: reach = valid_bits
    if isinstance(tree,bool):
        yield path,tree,reach
    else:
        atom, high, low = tree
        yield from leaves(high,high_masks,valid_bits,path+(1,),reach & high_masks[atom])
        yield from leaves(low,high_masks,valid_bits,path+(2,),reach & (valid_bits ^ high_masks[atom]))


def decision_mask(tree, high_masks, valid_bits):
    result = np.zeros_like(valid_bits)
    for _, action, reached in leaves(tree,high_masks,valid_bits):
        if action: result |= reached
    return result


def compile_tree(tree, atoms):
    if isinstance(tree,bool): return 'stop' if tree else 'continue'
    index, high, low = tree
    name, kind, cut = atoms[index]
    if kind == 'bool': predicate = {'op':'eq','args':[{'feature':name},{'bool':True}]}
    else: predicate = {'op':'gte','args':[{'feature':name},{kind:int(cut) if kind=='int' else float(cut)}]}
    return {'if':predicate,'then':compile_tree(high,atoms),'else':compile_tree(low,atoms)}


def fit(rows, condition, risk, profile, base_names, training_groups):
    from fitting import guard
    from contract import CONDITIONS, GROUPS
    from fannagent.api import validate_policy
    data = prepare(rows,condition,profile,base_names,training_groups)
    atoms, high_masks = atoms_for(data)
    width = DESIGN['beam_width']; beam = [(False,np.zeros_like(data.valid_bits)),(True,data.valid_bits.copy())]
    candidates_scored = 0; rounds = 0
    for step in range(DESIGN['growth_rounds']):
        pool = list(beam)
        for tree, before in beam:
            for path, action, reach in leaves(tree,high_masks,data.valid_bits):
                if len(path) >= DESIGN['tree_depth'] or not len(atoms): continue
                high = high_masks & reach[None,:]
                low = (data.valid_bits[None,:] ^ high_masks) & reach[None,:]
                # Exactly three cases per sorted vector group; no filter/cp replication
                # can count as another independent group for leaf support.
                support_h = (high != 0).reshape(len(atoms),-1,3).any(axis=2).sum(axis=1)
                support_l = (low != 0).reshape(len(atoms),-1,3).any(axis=2).sum(axis=1)
                allowed = np.flatnonzero((support_h >= DESIGN['minimum_leaf_groups']) &
                                         (support_l >= DESIGN['minimum_leaf_groups']))
                outside = before & (data.valid_bits ^ reach)
                for orientation, choices in ((True,high),(False,low)):
                    masks = choices[allowed] | outside[None,:]
                    if not len(masks): continue
                    values = scores(data,masks,risk); candidates_scored += len(masks)
                    order = sorted(range(len(values)), key=lambda j:(-float(values[j]),int(allowed[j])))
                    distinct = set()
                    for j in order:
                        mask_key = masks[j].tobytes()
                        if mask_key in distinct: continue
                        distinct.add(mask_key)
                        atom = int(allowed[j]); subtree = (atom,orientation,not orientation)
                        pool.append((replace(tree,path,subtree),masks[j].copy()))
                        if len(distinct) == width: break
        evaluated = scores(data,np.stack([p[1] for p in pool]),risk)
        ranked = sorted(zip(evaluated,pool),key=lambda item:(-float(item[0]),nodes(item[1][0]),repr(item[1][0])))
        next_beam = []; seen = set()
        for value, item in ranked:
            key = item[1].tobytes()
            if key in seen: continue
            seen.add(key); next_beam.append(item)
            if len(next_beam) == width: break
        rounds = step+1
        if [repr(p[0]) for p in next_beam] == [repr(p[0]) for p in beam]:
            beam = next_beam; break
        beam = next_beam
    tree, mask = beam[0]
    raw = {'name':'offline-first-stop-'+condition+'-'+digest([sorted(training_groups),risk])[:12],
           'feature_groups':GROUPS+(['local_filter'] if CONDITIONS[condition]['local_filter'] else []),
           'root':guard(compile_tree(tree,atoms),data.checkpoints)}
    artifact = validate_policy(raw,profile)
    first = first_indices(mask,len(data.checkpoints))
    return raw, {'condition':condition,'risk':risk,'training_groups':sorted(training_groups),
        'policy_hash':artifact.policy_hash,'decision_nodes_without_guard':nodes(tree),
        'candidate_thresholds':len(atoms),'candidate_scores_computed':candidates_scored,
        'growth_rounds':rounds,'training_objective':float(scores(data,mask,risk)[0]),
        'training_first_stops':{q['query_id']:None if int(j)==len(data.checkpoints) else data.checkpoints[int(j)] for q,j in zip(data.rows,first)}}
