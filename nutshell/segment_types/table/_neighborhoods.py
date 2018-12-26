from itertools import takewhile, permutations
from ._classes import Coord

NBHD_SETS = (
  # for containment-checking
  (frozenset({'E', 'W'}), 'oneDimensional'),
  (frozenset({'N', 'E', 'S', 'W'}), 'vonNeumann'),
  (frozenset({'N', 'E', 'SE', 'S', 'W', 'NW'}), 'hexagonal'),
  (frozenset({'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'}), 'Moore'),
)

ORDERED_NBHDS = {
  'oneDimensional': ('E', 'W'),
  'vonNeumann': ('N', 'E', 'S', 'W'),
  'hexagonal': ('N', 'E', 'SE', 'S', 'W', 'NW'),
  'Moore': ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'),
}


class Neighborhood:
    def __init__(self, cdirs):
        self.cdirs = tuple(cdirs)
        self.coord_cdirs = tuple(map(Coord.from_name, cdirs))
        self._inv = dict(enumerate(cdirs, 1))
        self.idxes = {v: k for k, v in self._inv.items()}
        self.symmetrical = all(c.inv.name in self for c in self.coord_cdirs)
    
    def __contains__(self, item):
        return item in self.idxes
    
    def __getitem__(self, item):
        return self.idxes[item]
    
    def __iter__(self):
        yield from self.cdirs
    
    def __len__(self):
        return len(self.cdirs)
    
    def __repr__(self):
        return f'Neighborhood({self.cdirs!r})'
    
    def __str__(self):
        return '\n'.join(map(' '.join, self.to_list()))
    
    def get(self, item, default=None):
        return self.idxes.get(item, default)
    
    def to_list(self, blank='.'):
        return [[str(self.get(cdir, blank)) for cdir in row] for row in (('NW', 'N', 'NE'), ('W', 'C', 'E'), ('SW', 'S', 'SE'))]
    
    def cdir_at(self, idx):
        if idx < 1:  # like negative access on python sequences
            return self._inv[len(self) + idx]
        return self._inv[idx]
    
    def gollyizer_for(self, tbl):
        return get_gollyizer(tbl, self.cdirs)
    
    def reflect_across(self, endpoint):
        if not isinstance(endpoint, tuple):
            raise TypeError('Endpoint of line of reflection should be given as tuple of compass directions')
        a, b = endpoint
        if isinstance(a, str):
            a = Coord.from_name(a)
        if isinstance(b, str):
            b = Coord.from_name(b)
        if a != b and a.cw(1) != b:
            raise ValueError('Endpoint compass directions of a line of reflection must be both adjacent and given in clockwise order')
        to_check = [cdir for cdir in self.coord_cdirs if cdir not in {a, b, a.inv, b.inv}]
        if len(to_check) % 2 or any(c.inv.name not in self for c in to_check):
            raise ValueError('Neighborhood is asymmetrical across the requested line of reflection')
        if a == b:
            # i think the naive approach is the only way to go :(
            while a.name not in self:
                a = a.ccw(1)
            while b.name not in self:
                b = b.cw(1)
        d = {}
        try:
            for cdir in self.coord_cdirs:
                d[cdir.name] = a.cw(b.ccw_distance(cdir, self), self).name
        except KeyError as e:
            raise ValueError(f'Neighborhood does not contain {e}')
        r = {cdir: self[orig_cdir] for orig_cdir, cdir in d.items()}
        return Neighborhood(sorted(r, key=r.get))
    
    def reflections_across(self, endpoint):
        return (self, self.reflect_across(endpoint))
    
    def rotate_by(self, offset):
        return Neighborhood(self.cdirs[offset:] + self.cdirs[:offset])
    
    def rotations_by(self, amt):
        if len(self) % amt:
            raise ValueError(f'Neighborhood cannot be rotated evenly by {amt}')
        if not self.symmetrical:
            raise ValueError('Neighborhood is asymmetrical, cannot be rotated except by 1')
        return [self.rotate_by(offset) for offset in range(0, len(self), len(self) // amt)]
    
    def permutations(self, cdirs=None):
        if cdirs is None:
            cdirs = self.cdirs
        permuted_cdirs = set(cdirs)
        return [Neighborhood(next(permute) if c in permuted_cdirs else c for c in self) for permute in map(iter, permutations(cdirs))]


def get_gollyizer(tbl, nbhd):
    nbhd_set = set(nbhd)
    for s, name in NBHD_SETS:
        if nbhd_set <= s:
            tbl.directives['neighborhood'] = name
            if nbhd_set < s:
                return fill.__get__(ORDERED_NBHDS[name])
            return lambda tbl, napkin, _anys: reorder(ORDERED_NBHDS[name], tbl, napkin)
    raise ValueError('Invalid (non-Moore-subset) neighborhood {nbhd_set}}')


def reorder(ordered_nbhd, tbl, napkin):
    cdir_at = tbl.neighborhood.cdir_at
    d = {cdir_at(k): v for k, v in enumerate(napkin, 1)}
    return [d[cdir] for cdir in ordered_nbhd]


def fill(ordered_nbhd, tbl, napkin, anys):  # anys == usages of `any`
    if isinstance(anys, int):
        anys = set(range(anys))
    cdir_at = tbl.neighborhood.cdir_at
    d = {cdir_at(k): v for k, v in enumerate(napkin, 1)}
    available_tags = [i for i in range(10) if i not in anys]
    # (ew, but grabbing VarName object)
    tbl.vars.inv[tbl.vars['any']].update_rep(
      max(anys) + len(ordered_nbhd) - len(tbl.neighborhood) - sum(takewhile(max(anys).__gt__, available_tags))
      )
    tagged_names = (f'any.{i}' for i in available_tags)
    # `or` because this needs lazy evaluation
    return [d.get(cdir) or next(tagged_names) for cdir in ordered_nbhd]
