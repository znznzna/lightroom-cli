"""catalog.findPhotos / searchPhotos run as real plugin Lua against a small fake catalog.

Replaces tests that registered a canned response on the mock server and read it back
(codex-tests #10): those passed even if the Lua filters, the searchPhotos delegation or the
incomplete-result reporting were broken, because no plugin code ran.
"""

import pytest

from tests.test_plugin_lua_unit import _load, _make_runtime

# Each photo: raw metadata, formatted metadata and keyword names, as Lightroom would return them
PHOTOS = [
    {
        "id": 1,
        "raw": {
            "rating": 5,
            "pickStatus": 1,
            "colorNameForLabel": "red",
            "fileFormat": "RAW",
            "path": "/Photos/2024/IMG_001.CR3",
            "dateTimeOriginal": "2024-06-15T10:00:00",
        },
        "fmt": {"fileName": "IMG_001.CR3", "cameraModel": "Canon EOS R5", "dateTimeOriginal": "2024-06-15T10:00:00"},
        "keywords": ["Landscape", "Mountain"],
    },
    {
        "id": 2,
        "raw": {
            "rating": 3,
            "pickStatus": 0,
            "colorNameForLabel": "",
            "fileFormat": "JPG",
            "path": "/Photos/2023/IMG_002.jpg",
            "dateTimeOriginal": "2023-12-31T23:30:00",
        },
        "fmt": {"fileName": "IMG_002.jpg", "cameraModel": "FUJIFILM X-T5", "dateTimeOriginal": "2023-12-31T23:30:00"},
        "keywords": ["Portrait"],
    },
    {
        "id": 3,
        "raw": {
            "rating": 0,
            "pickStatus": -1,
            "colorNameForLabel": "blue",
            "fileFormat": "RAW",
            "path": "/Photos/2024/DSC_003.NEF",
            "dateTimeOriginal": "2024-01-01T00:00:00",
        },
        "fmt": {"fileName": "DSC_003.NEF", "cameraModel": "NIKON Z 8", "dateTimeOriginal": "2024-01-01T00:00:00"},
        "keywords": [],
    },
    {
        "id": 4,
        "raw": {
            "rating": 4,
            "pickStatus": 0,
            "colorNameForLabel": "none",
            "fileFormat": "JPG",
            "path": "/Photos/2024/IMG_004.jpg",
            "dateTimeOriginal": None,
        },
        "fmt": {"fileName": "IMG_004.jpg", "cameraModel": "", "dateTimeOriginal": ""},
        "keywords": ["mountain lake"],
    },
]


@pytest.fixture
def rt():
    rt = _make_runtime()
    rt.execute(
        """
        local function makePhoto(spec)
            local keywords = {}
            for i, name in ipairs(spec.keywords) do
                keywords[i] = { getName = function() return name end }
            end
            return {
                localIdentifier = spec.id,
                getRawMetadata = function(self, key)
                    if key == "keywords" then return keywords end
                    return spec.raw[key]
                end,
                getFormattedMetadata = function(self, key) return spec.fmt[key] end,
            }
        end
        PHOTOS = {}
        function ADD_PHOTO(spec) PHOTOS[#PHOTOS + 1] = makePhoto(spec) end
        CATALOG = {
            withReadAccessDo = function(self, func) func() end,
            getAllPhotos = function(self) return PHOTOS end,
        }
        ABORT = nil  -- set to "timeout" / "cancelled" to make the router abort at the next chunk
        local router = {
            shouldAbort = function(self) return ABORT ~= nil end,
            isCancelled = function(self) return ABORT == "cancelled" end,
            sendStreamEvent = function() end,
        }
        _G.LightroomPythonBridge = { commandRouter = router }
        local permissive_import = import
        function import(name)
            if name == 'LrApplication' then
                return { activeCatalog = function() return CATALOG end }
            end
            if name == 'LrTasks' then
                return { pcall = pcall, yield = function() end }
            end
            if name == 'LrDate' then
                error("LrDate unavailable: use the formatted date")
            end
            return permissive_import(name)
        end
        RESPONSES = {}
        function RECORD(response) RESPONSES[#RESPONSES + 1] = response end
        """
    )
    for photo in PHOTOS:
        rt.globals().ADD_PHOTO(_to_lua(rt, photo))
    _load(rt, "CatalogModule")
    return rt


def _to_lua(rt, value):
    if isinstance(value, dict):
        return rt.table_from({k: _to_lua(rt, v) for k, v in value.items() if v is not None})
    if isinstance(value, list):
        return rt.table_from([_to_lua(rt, v) for v in value])
    return value


def _run(rt, command, params):
    rt.globals().RESPONSES = rt.table()
    handler = rt.eval(f"require('CatalogModule').{command}")
    handler(_to_lua(rt, params), rt.globals().RECORD)
    responses = rt.globals().RESPONSES
    assert len(responses) == 1, "the handler must answer exactly once"
    return responses[1]


def _ids(response):
    return [photo["id"] for photo in response["result"]["photos"].values()]


@pytest.mark.parametrize(
    "search, expected",
    [
        ({}, [1, 2, 3, 4]),
        ({"folderPath": "2024"}, [1, 3, 4]),
        ({"folderPath": "/Photos/2023/"}, [2]),
        ({"filename": "IMG_"}, [1, 2, 4]),
        ({"rating": 4, "ratingOp": ">="}, [1, 4]),
        ({"rating": 3}, [2]),
        ({"rating": 3, "ratingOp": "<"}, [3]),
        ({"flag": "pick"}, [1]),
        ({"flag": "reject"}, [3]),
        ({"flag": "none"}, [2, 4]),
        ({"colorLabel": "red"}, [1]),
        ({"colorLabel": "none"}, [2, 4]),  # "" and "none" both mean no label
        ({"fileFormat": "RAW"}, [1, 3]),
        ({"camera": "canon"}, [1]),  # case-insensitive substring
        ({"keyword": "MOUNTAIN"}, [1, 4]),  # case-insensitive substring of any keyword
        ({"captureDateFrom": "2024-01-01"}, [1, 3]),  # photo 4 has no capture date
        ({"captureDateTo": "2023-12-31"}, [2]),  # date-only upper bound includes that whole day
        ({"captureDateFrom": "2024-01-01", "captureDateTo": "2024-01-01"}, [3]),
        ({"folderPath": "2024", "fileFormat": "JPG"}, [4]),  # filters combine with AND
        ({"camera": "sony"}, []),
    ],
)
def test_find_photos_filters(rt, search, expected):
    response = _run(rt, "findPhotos", {"searchDesc": search})
    assert sorted(_ids(response)) == expected
    assert response["result"]["total"] == len(expected)


def test_find_photos_paginates_after_filtering(rt):
    response = _run(rt, "findPhotos", {"searchDesc": {"folderPath": "2024"}, "limit": 2, "offset": 1})
    result = response["result"]
    assert _ids(response) == [3, 4]
    assert (result["total"], result["returned"], result["offset"], result["limit"]) == (3, 2, 1, 2)


def test_find_photos_returns_metadata_fields(rt):
    response = _run(rt, "findPhotos", {"searchDesc": {"filename": "IMG_001"}})
    photo = response["result"]["photos"][1]
    assert dict(photo) == {
        "id": 1,
        "filename": "IMG_001.CR3",
        "path": "/Photos/2024/IMG_001.CR3",
        "captureTime": "2024-06-15T10:00:00",
        "fileFormat": "RAW",
        "rating": 5,
        "pickStatus": 1,
        "colorLabel": "red",
    }


def test_unknown_filter_key_is_reported_not_ignored_silently(rt):
    response = _run(rt, "findPhotos", {"searchDesc": {"folder": "2024"}})
    assert list(response["result"]["warnings"].values()) == ["Unknown filter key: folder"]
    assert response["result"]["total"] == 4


def test_non_numeric_rating_is_rejected(rt):
    response = _run(rt, "findPhotos", {"searchDesc": {"rating": "5"}})
    assert response["error"]["code"] == "INVALID_PARAM"


def test_search_photos_delegates_to_find_photos(rt):
    response = _run(rt, "searchPhotos", {"criteria": {"folderPath": "2024"}, "limit": 2, "offset": 0})
    result = response["result"]
    assert _ids(response) == [1, 3]
    assert result["total"] == 3
    assert result["hasMore"] is True  # legacy field added by searchPhotos on top of findPhotos


def test_search_photos_has_more_is_false_on_last_page(rt):
    response = _run(rt, "searchPhotos", {"criteria": {"folderPath": "2024"}, "limit": 2, "offset": 2})
    assert response["result"]["hasMore"] is False


@pytest.mark.parametrize("reason", ["timeout", "cancelled"])
def test_abort_marks_result_incomplete(rt, reason):
    rt.globals().ABORT = reason
    response = _run(rt, "findPhotos", {"searchDesc": {}, "_requestId": "r1"})
    result = response["result"]
    assert result["incomplete"] is True
    assert result["reason"] == reason
    assert result["returned"] == 0


def test_failing_chunk_is_reported_as_partial_error(rt):
    # A photo whose metadata read throws, as a deleted or offline photo can
    rt.execute(
        "PHOTOS[2].getRawMetadata = function() error('photo is gone') end; "
        "PHOTOS[2].getFormattedMetadata = PHOTOS[2].getRawMetadata"
    )
    response = _run(rt, "findPhotos", {"searchDesc": {"rating": 0, "ratingOp": ">="}})
    result = response["result"]
    assert result["incomplete"] is True
    assert result["reason"] == "chunk_errors"
    errors = list(result["partialErrors"].values())
    assert errors and "photo is gone" in errors[0]["error"]


def test_complete_result_is_not_marked_incomplete(rt):
    result = _run(rt, "findPhotos", {"searchDesc": {}})["result"]
    assert result["incomplete"] is None
    assert result["partialErrors"] is None
