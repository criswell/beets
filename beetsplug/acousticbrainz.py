# -*- coding: utf-8 -*-
# This file is part of beets.
# Copyright 2015-2016, Ohm Patel.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

"""Fetch various AcousticBrainz metadata using MBID.
"""
from __future__ import division, absolute_import, print_function

import requests

from collections import defaultdict
from beets import plugins, ui

ACOUSTIC_BASE = "https://acousticbrainz.org/"
LEVELS = ["/low-level", "/high-level"]
ABSCHEME = {
    'highlevel': {
        'danceability': {
            'all': {
                'danceable': 'danceable'
            }
        },
        'gender': {
            'value': 'gender'
        },
        'genre_rosamerica': {
            'value': 'genre_rosamerica'
        },
        'mood_acoustic': {
            'all': {
                'acoustic': 'mood_acoustic'
            }
        },
        'mood_aggressive': {
            'all': {
                'aggressive': 'mood_aggressive'
            }
        },
        'mood_electronic': {
            'all': {
                'electronic': 'mood_electronic'
            }
        },
        'mood_happy': {
            'all': {
                'happy': 'mood_happy'
            }
        },
        'mood_party': {
            'all': {
                'party': 'mood_party'
            }
        },
        'mood_relaxed': {
            'all': {
                'relaxed': 'mood_relaxed'
            }
        },
        'mood_sad': {
            'all': {
                'sad': 'mood_sad'
            }
        },
        'ismir04_rhythm': {
            'value': 'rhythm'
        },
        'tonal_atonal': {
            'all': {
                'tonal': 'tonal'
            }
        },
        'voice_instrumental': {
            'value': 'voice_instrumental'
        },
    },
    'lowlevel': {
        'average_loudness': 'average_loudness'
    },
    'rhythm': {
        'bpm': 'bpm'
    },
    'tonal': {
        'chords_changes_rate': 'chords_changes_rate',
        'chords_key': 'chords_key',
        'chords_number_rate': 'chords_number_rate',
        'chords_scale': 'chords_scale',
        'key_key': ('initial_key', 0),
        'key_scale': ('initial_key', 1),
        'key_strength': 'key_strength'

    }
}


class AcousticPlugin(plugins.BeetsPlugin):
    def __init__(self):
        super(AcousticPlugin, self).__init__()

        self.config.add({'auto': True})
        if self.config['auto']:
            self.register_listener('import_task_files',
                                   self.import_task_files)

    def commands(self):
        cmd = ui.Subcommand('acousticbrainz',
                            help=u"fetch metadata from AcousticBrainz")

        def func(lib, opts, args):
            items = lib.items(ui.decargs(args))
            self._fetch_info(items, ui.should_write())

        cmd.func = func
        return [cmd]

    def import_task_files(self, session, task):
        """Function is called upon beet import.
        """
        self._fetch_info(task.imported_items(), False)

    def _get_data(self, mbid):
        data = {}
        for url in _generate_urls(mbid):
            self._log.debug(u'fetching URL: {}', url)

            try:
                res = requests.get(url)
            except requests.RequestException as exc:
                self._log.info(u'request error: {}', exc)
                return {}

            if res.status_code == 404:
                self._log.info(u'recording ID {} not found', mbid)
                return {}

            try:
                data.update(res.json())
            except ValueError:
                self._log.debug(u'Invalid Response: {}', res.text)
                return {}

        return data

    def _fetch_info(self, items, write):
        """Get data from AcousticBrainz for the items.
        """
        for item in items:
            if not item.mb_trackid:
                continue

            self._log.info(u'getting data for: {}', item)
            data = self._get_data(item.mb_trackid)
            if data:
                for attr, val in self._map_dict_to_scheme(data, ABSCHEME):
                    self._log.info(u'attribute {} of {} set to {}',
                                   attr,
                                   item,
                                   val)
                    setattr(item, attr, val)
                item.store()
                if write:
                    item.try_write()

    def _map_dict_to_scheme(self, dictionary, scheme):
        composites = defaultdict(lambda: DefaultList(''))
        for yielded in self._dict_to_scheme_child(dictionary,
                                                  scheme,
                                                  composites):
            yield yielded
        for k, v in composites.items():
            yield k, ' '.join(v)

    def _dict_to_scheme_child(self, subdict, subscheme, composites):
        for k, v in subscheme.items():
            if k in subdict:
                if type(v) == dict:
                    for yielded in self._dict_to_scheme_child(subdict[k],
                                                              v,
                                                              composites):
                        yield yielded
                elif type(v) == tuple:
                    composites[v[0]][v[1]] = subdict[k]
                else:
                    yield (v, subdict[k])
            else:
                self._log.debug(u'Data {} could not be mapped to scheme {} '
                                u'because key {} was not found', subdict, v, k)


def _generate_urls(mbid):
    """Generates AcousticBrainz end point url for given MBID.
    """
    for level in LEVELS:
        yield ACOUSTIC_BASE + mbid + level


class DefaultList(list):
    """A list which extends itself with the default value provided to the
    constructor when indexed further than its length.
    """
    def __init__(self, default):
        self._default = default

    def __setitem__(self, index, value):
        while len(self) < index:
            self.append(self._default)
        self.append(value)

    def __getitem__(self, index):
        while len(self) <= index:
            self.append(self._default)
        return list.__getitem__(self, index)
