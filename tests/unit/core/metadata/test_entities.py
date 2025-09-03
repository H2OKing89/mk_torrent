"""
Tests for rich entity model (AudiobookMetaRich and supporting entities).
"""

from mk_torrent.core.metadata.entities import (
    AudiobookMetaRich,
    PersonRef,
    GenreTag,
    SeriesRef,
    Chapter,
)


class TestPersonRef:
    """Test PersonRef entity."""

    def test_default_initialization(self):
        person = PersonRef(name="Test Author")
        assert person.name == "Test Author"
        assert person.asin is None
        assert person.role == ""

    def test_full_initialization(self):
        person = PersonRef(name="Dojyomaru", asin="B06W5GKCZW", role="author")
        assert person.name == "Dojyomaru"
        assert person.asin == "B06W5GKCZW"
        assert person.role == "author"


class TestGenreTag:
    """Test GenreTag entity."""

    def test_default_initialization(self):
        genre = GenreTag(name="Fantasy")
        assert genre.name == "Fantasy"
        assert genre.type == "genre"
        assert genre.asin is None

    def test_tag_initialization(self):
        tag = GenreTag(name="Epic", type="tag", asin="18580615011")
        assert tag.name == "Epic"
        assert tag.type == "tag"
        assert tag.asin == "18580615011"


class TestSeriesRef:
    """Test SeriesRef entity."""

    def test_default_initialization(self):
        series = SeriesRef()
        assert series.name == ""
        assert series.position_str == ""
        assert series.position_num is None
        assert series.asin is None

    def test_full_initialization(self):
        series = SeriesRef(
            name="How a Realist Hero Rebuilt the Kingdom",
            position_str="3",
            position_num=3.0,
            asin="B0C37XK8SV",
        )
        assert series.name == "How a Realist Hero Rebuilt the Kingdom"
        assert series.position_str == "3"
        assert series.position_num == 3.0
        assert series.asin == "B0C37XK8SV"


class TestChapter:
    """Test Chapter entity."""

    def test_initialization(self):
        chapter = Chapter(index=1, title="Opening Credits", start_ms=0)
        assert chapter.index == 1
        assert chapter.title == "Opening Credits"
        assert chapter.start_ms == 0
        assert chapter.kind == "chapter"

    def test_with_kind(self):
        chapter = Chapter(index=1, title="Opening Credits", start_ms=0, kind="credits")
        assert chapter.kind == "credits"


class TestAudiobookMetaRich:
    """Test AudiobookMetaRich comprehensive model."""

    def test_default_initialization(self):
        audiobook = AudiobookMetaRich()
        assert audiobook.title == ""
        assert audiobook.subtitle == ""
        assert isinstance(audiobook.series, SeriesRef)
        assert audiobook.volume == ""
        assert audiobook.authors == []
        assert audiobook.narrators == []
        assert audiobook.genres == []
        assert audiobook.chapters == []
        assert audiobook.files == []
        assert audiobook.provenance == []

    def test_with_rich_entities(self):
        # Create rich entities
        author = PersonRef(name="Dojyomaru", asin="B06W5GKCZW", role="author")
        narrator = PersonRef(name="BJ Harrison", role="narrator")
        series = SeriesRef(
            name="How a Realist Hero Rebuilt the Kingdom",
            position_str="3",
            position_num=3.0,
        )
        genre = GenreTag(name="Fantasy", type="genre")
        chapter = Chapter(index=1, title="Prologue", start_ms=1000)

        audiobook = AudiobookMetaRich(
            title="How a Realist Hero Rebuilt the Kingdom: Volume 3",
            series=series,
            volume="03",
            authors=[author],
            narrators=[narrator],
            genres=[genre],
            chapters=[chapter],
            asin="B0C8ZW5N6Y",
            year=2023,
        )

        assert audiobook.title == "How a Realist Hero Rebuilt the Kingdom: Volume 3"
        assert audiobook.series.name == "How a Realist Hero Rebuilt the Kingdom"
        assert audiobook.volume == "03"
        assert len(audiobook.authors) == 1
        assert audiobook.authors[0].name == "Dojyomaru"
        assert len(audiobook.narrators) == 1
        assert audiobook.narrators[0].name == "BJ Harrison"
        assert len(audiobook.genres) == 1
        assert audiobook.genres[0].name == "Fantasy"
        assert len(audiobook.chapters) == 1
        assert audiobook.chapters[0].title == "Prologue"

    def test_to_dict(self):
        audiobook = AudiobookMetaRich(title="Test Book", volume="01")
        data = audiobook.to_dict()

        assert isinstance(data, dict)
        assert data["title"] == "Test Book"
        assert data["volume"] == "01"
        assert "series" in data
        assert "authors" in data

    def test_from_dict(self):
        data = {
            "title": "Test Book",
            "volume": "01",
            "authors": [{"name": "Test Author", "role": "author"}],
            "series": {"name": "Test Series", "position_str": "1"},
        }

        audiobook = AudiobookMetaRich.from_dict(data)
        assert audiobook.title == "Test Book"
        assert audiobook.volume == "01"
        assert len(audiobook.authors) == 1
        assert audiobook.authors[0].name == "Test Author"
        assert audiobook.series.name == "Test Series"

    def test_to_simple_audiobook_meta(self):
        """Test conversion to simple AudiobookMeta format."""
        audiobook = AudiobookMetaRich(
            title="Test Book",
            author_primary="Test Author",
            narrator_primary="Test Narrator",
            volume="01",
            year=2023,
            asin="TEST123",
            duration_sec=3600,
        )
        audiobook.series.name = "Test Series"
        audiobook.audio.codec = "AAC"
        audiobook.audio.bitrate_mode = "CBR"
        audiobook.audio.bitrate_bps = 128000

        simple_data = audiobook.to_simple_audiobook_meta()

        assert simple_data["title"] == "Test Book"
        assert simple_data["author"] == "Test Author"
        assert simple_data["narrator"] == "Test Narrator"
        assert simple_data["series"] == "Test Series"
        assert simple_data["volume"] == "01"
        assert simple_data["year"] == 2023
        assert simple_data["asin"] == "TEST123"
        assert simple_data["duration_sec"] == 3600
        assert simple_data["format"] == "AAC"
        assert simple_data["encoding"] == "CBR@128000"


class TestRichEntityIntegration:
    """Test integration between rich entities and existing system."""

    def test_import_from_main_module(self):
        """Test that rich entities can be imported from main metadata module."""
        from mk_torrent.core.metadata import (
            AudiobookMetaRich,
            PersonRef,
            GenreTag,
            SeriesRef,
        )

        # Should not raise ImportError
        assert AudiobookMetaRich is not None
        assert PersonRef is not None
        assert GenreTag is not None
        assert SeriesRef is not None

    def test_backward_compatibility_preserved(self):
        """Test that existing AudiobookMeta still works."""
        from mk_torrent.core.metadata import AudiobookMeta

        # Existing simple model should still work
        audiobook = AudiobookMeta(title="Test", author="Author", year=2023)
        assert audiobook.title == "Test"
        assert audiobook.author == "Author"
        assert audiobook.year == 2023

        # Conversion methods should work
        data = audiobook.to_dict()
        audiobook2 = AudiobookMeta.from_dict(data)
        assert audiobook2.title == "Test"
