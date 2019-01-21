"""Manipulates installer files"""
import os
from lutris import pga
from lutris import settings
from lutris.installer.errors import ScriptingError, FileNotAvailable
from lutris.util.log import logger
from lutris.util import system


class InstallerFile:
    """Representation of a file in the `files` sections of an installer"""
    def __init__(self, game_slug, file_id, file_meta):
        self.game_slug = game_slug
        self.id = file_id  # pylint: disable=invalid-name
        self.dest_file = None
        if isinstance(file_meta, dict):
            for field in ("url", "filename"):
                if field not in file_meta:
                    raise ScriptingError(
                        "missing field `%s` for file `%s`" % (field, file_id)
                    )
            self.url = file_meta["url"]
            self.filename = file_meta["filename"]
            self.referer = file_meta.get("referer")
            self.checksum = file_meta.get("checksum")
        else:
            self.url = file_meta
            self.filename = os.path.basename(file_meta)
            self.referer = None
            self.checksum = None

        if self.url.startswith("/"):
            self.url = "file://" + self.url

        if not self.filename:
            raise ScriptingError(
                "No filename provided, please provide 'url' and 'filename' parameters in the script"
            )

    @property
    def cache_path(self):
        """Return the directory used as a cache for the duration of the installation"""
        return os.path.join(settings.CACHE_DIR, "installer/%s" % self.game_slug)

    def get_download_info(self):
        """Retrieve the file locally"""
        if self.url.startswith(("$WINESTEAM", "$STEAM", "N/A")):
            raise FileNotAvailable()
        # Check for file availability in PGA
        pga_uri = pga.check_for_file(self.game_slug, self.id)
        if pga_uri:
            self.url = pga_uri

        dest_file = os.path.join(self.cache_path, self.filename)
        logger.debug("Downloading [%s]: %s to %s", self.id, self.url, dest_file)

        if os.path.exists(dest_file):
            os.remove(dest_file)
        self.dest_file = dest_file
        return self.dest_file

    def check_hash(self):
        """Checks the checksum of `file` and compare it to `value`

        Args:
            checksum (str): The checksum to look for (type:hash)
            dest_file (str): The path to the destination file
            dest_file_uri (str): The uri for the destination file
        """
        if not self.checksum or not self.dest_file:
            return
        try:
            hash_type, expected_hash = self.checksum.split(':', 1)
        except ValueError:
            raise ScriptingError("Invalid checksum, expected format (type:hash) ", self.checksum)

        if system.get_file_checksum(self.dest_file, hash_type) != expected_hash:
            raise ScriptingError(hash_type.capitalize() + " checksum mismatch ", self.checksum)
