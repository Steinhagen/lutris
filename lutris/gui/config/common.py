"""Shared config dialog stuff"""
import os
from gi.repository import Gtk, Pango, GLib
from lutris.game import Game
from lutris.config import LutrisConfig, TEMP_CONFIG
from lutris import runners
from lutris import settings
from lutris.gui.widgets.common import VBox, SlugEntry, NumberEntry, Label, FileChooserEntry
from lutris.gui.config.boxes import GameBox, RunnerBox, SystemBox
from lutris.gui.dialogs import ErrorDialog
from lutris.gui.dialogs.runners import RunnersDialog
from lutris.gui.widgets.utils import (
    get_pixbuf_for_game,
    get_pixbuf,
    BANNER_SIZE,
    ICON_SIZE,
)
from lutris.util.strings import slugify
from lutris.util import datapath
from lutris.util import resources


# pylint: disable=too-many-instance-attributes
class GameDialogCommon:
    """Mixin for config dialogs"""
    no_runner_label = "Select a runner in the Game Info tab"

    def __init__(self):
        self.notebook = None
        self.vbox = None
        self.name_entry = None
        self.runner_box = None

    @staticmethod
    def build_scrolled_window(widget):
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(widget)
        return scrolled_window

    def build_notebook(self):
        self.notebook = Gtk.Notebook()
        self.vbox.pack_start(self.notebook, True, True, 10)

    def build_tabs(self, config_level):
        self.timer_id = None
        if config_level == "game":
            self._build_info_tab()
            self._build_game_tab()
        if config_level in ("game", "runner"):
            self._build_runner_tab(config_level)
        if config_level == "system":
            self._build_prefs_tab()
        self._build_system_tab(config_level)

    def _build_info_tab(self):
        info_box = VBox()

        if self.game:
            info_box.pack_start(self._get_banner_box(), False, False, 6)  # Banner

        info_box.pack_start(self._get_name_box(), False, False, 6)  # Game name

        if self.game:
            info_box.pack_start(self._get_slug_box(), False, False, 6)  # Game id

        self.runner_box = self._get_runner_box()
        info_box.pack_start(self.runner_box, False, False, 6)  # Runner

        info_box.pack_start(self._get_year_box(), False, False, 6)  # Year

        info_sw = self.build_scrolled_window(info_box)
        self._add_notebook_tab(info_sw, "Game info")

    def _build_prefs_tab(self):
        prefs_box = VBox()
        prefs_box.pack_start(self._get_game_cache_box(), False, False, 6)
        info_sw = self.build_scrolled_window(prefs_box)
        self._add_notebook_tab(info_sw, "Lutris preferences")

    def _get_game_cache_box(self):
        box = Gtk.Box(spacing=12, margin_right=12, margin_left=12)
        label = Label("Cache path")
        box.pack_start(label, False, False, 0)
        cache_path = settings.read_setting("pga_cache_path")
        path_chooser = FileChooserEntry(
            title="Set the folder for the cache path",
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            default_path=cache_path
        )
        path_chooser.entry.connect("changed", self._on_cache_path_set)
        box.pack_start(path_chooser, True, True, 0)
        return box

    def _on_cache_path_set(self, entry):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
        self.timer_id = GLib.timeout_add(1000, self.save_cache_setting, entry.get_text())

    def save_cache_setting(self, value):
        settings.write_setting("pga_cache_path", value)
        GLib.source_remove(self.timer_id)
        self.timer_id = None
        return False

    def _get_name_box(self):
        box = Gtk.Box(spacing=12, margin_right=12, margin_left=12)
        label = Label("Name")
        box.pack_start(label, False, False, 0)
        self.name_entry = Gtk.Entry()
        if self.game:
            self.name_entry.set_text(self.game.name)
        box.pack_start(self.name_entry, True, True, 0)
        return box

    def _get_slug_box(self):
        slug_box = Gtk.Box(spacing=12, margin_right=12, margin_left=12)

        label = Label("Identifier")
        slug_box.pack_start(label, False, False, 0)

        self.slug_entry = SlugEntry()
        self.slug_entry.set_text(self.game.slug)
        self.slug_entry.set_sensitive(False)
        self.slug_entry.connect("activate", self.on_slug_entry_activate)
        slug_box.pack_start(self.slug_entry, True, True, 0)

        self.slug_change_button = Gtk.Button("Change")
        self.slug_change_button.connect("clicked", self.on_slug_change_clicked)
        slug_box.pack_start(self.slug_change_button, False, False, 0)

        return slug_box

    def _get_runner_box(self):
        runner_box = Gtk.Box(spacing=12, margin_right=12, margin_left=12)

        runner_label = Label("Runner")
        runner_box.pack_start(runner_label, False, False, 0)

        self.runner_dropdown = self._get_runner_dropdown()
        runner_box.pack_start(self.runner_dropdown, True, True, 0)

        install_runners_btn = Gtk.Button("Install runners")
        install_runners_btn.connect("clicked", self.on_install_runners_clicked)
        runner_box.pack_start(install_runners_btn, True, True, 0)

        return runner_box

    def _get_banner_box(self):
        banner_box = Gtk.Box(spacing=12, margin_right=12, margin_left=12)

        label = Label("")
        banner_box.pack_start(label, False, False, 0)

        self.banner_button = Gtk.Button()
        self._set_image("banner")
        self.banner_button.connect("clicked", self.on_custom_image_select, "banner")
        banner_box.pack_start(self.banner_button, False, False, 0)

        reset_banner_button = Gtk.Button.new_from_icon_name(
            "edit-clear", Gtk.IconSize.MENU
        )
        reset_banner_button.set_relief(Gtk.ReliefStyle.NONE)
        reset_banner_button.set_tooltip_text("Remove custom banner")
        reset_banner_button.connect(
            "clicked", self.on_custom_image_reset_clicked, "banner"
        )
        banner_box.pack_start(reset_banner_button, False, False, 0)

        self.icon_button = Gtk.Button()
        self._set_image("icon")
        self.icon_button.connect("clicked", self.on_custom_image_select, "icon")
        banner_box.pack_start(self.icon_button, False, False, 0)

        reset_icon_button = Gtk.Button.new_from_icon_name(
            "edit-clear", Gtk.IconSize.MENU
        )
        reset_icon_button.set_relief(Gtk.ReliefStyle.NONE)
        reset_icon_button.set_tooltip_text("Remove custom icon")
        reset_icon_button.connect("clicked", self.on_custom_image_reset_clicked, "icon")
        banner_box.pack_start(reset_icon_button, False, False, 0)

        return banner_box

    def _get_year_box(self):
        box = Gtk.Box(spacing=12, margin_right=12, margin_left=12)

        label = Label("Release year")
        box.pack_start(label, False, False, 0)

        self.year_entry = NumberEntry()
        if self.game:
            self.year_entry.set_text(str(self.game.year or ""))
        box.pack_start(self.year_entry, True, True, 0)

        return box

    def _set_image(self, image_format):
        assert image_format in ("banner", "icon")
        image = Gtk.Image()
        game_slug = self.game.slug if self.game else ""
        image.set_from_pixbuf(get_pixbuf_for_game(game_slug, image_format))
        if image_format == "banner":
            self.banner_button.set_image(image)
        else:
            self.icon_button.set_image(image)

    def _set_icon_image(self):
        image = Gtk.Image()
        game_slug = self.game.slug if self.game else ""
        image.set_from_pixbuf(get_pixbuf_for_game(game_slug, "banner"))
        self.banner_button.set_image(image)

    def _get_runner_dropdown(self):
        runner_liststore = self._get_runner_liststore()
        runner_dropdown = Gtk.ComboBox.new_with_model(runner_liststore)
        runner_dropdown.set_id_column(1)
        runner_index = 0
        if self.runner_name:
            for runner in runner_liststore:
                if self.runner_name == str(runner[1]):
                    break
                runner_index += 1
        runner_dropdown.set_active(runner_index)
        runner_dropdown.connect("changed", self.on_runner_changed)
        cell = Gtk.CellRendererText()
        cell.props.ellipsize = Pango.EllipsizeMode.END
        runner_dropdown.pack_start(cell, True)
        runner_dropdown.add_attribute(cell, "text", 0)
        return runner_dropdown

    @staticmethod
    def _get_runner_liststore():
        """Build a ListStore with available runners."""
        runner_liststore = Gtk.ListStore(str, str)
        runner_liststore.append(("Select a runner from the list", ""))
        for runner in runners.get_installed():
            description = runner.description
            runner_liststore.append(
                ("%s (%s)" % (runner.human_name, description), runner.name)
            )
        return runner_liststore

    def on_slug_change_clicked(self, widget):
        if self.slug_entry.get_sensitive() is False:
            widget.set_label("Apply")
            self.slug_entry.set_sensitive(True)
        else:
            self.change_game_slug()

    def on_slug_entry_activate(self, widget):
        self.change_game_slug()

    def change_game_slug(self):
        self.slug = self.slug_entry.get_text()
        self.slug_entry.set_sensitive(False)
        self.slug_change_button.set_label("Change")

    def on_install_runners_clicked(self, _button):
        runners_dialog = RunnersDialog()
        runners_dialog.connect("runner-installed", self._update_runner_dropdown)

    def _update_runner_dropdown(self, _widget):
        active_id = self.runner_dropdown.get_active_id()
        self.runner_dropdown.set_model(self._get_runner_liststore())
        self.runner_dropdown.set_active_id(active_id)

    def _build_game_tab(self):
        if self.game and self.runner_name:
            self.game.runner_name = self.runner_name
            try:
                self.game.runner = runners.import_runner(self.runner_name)()
            except runners.InvalidRunner:
                pass
            self.game_box = GameBox(self.lutris_config, self.game)
            game_sw = self.build_scrolled_window(self.game_box)
        elif self.runner_name:
            game = Game(None)
            game.runner_name = self.runner_name
            self.game_box = GameBox(self.lutris_config, game)
            game_sw = self.build_scrolled_window(self.game_box)
        else:
            game_sw = Gtk.Label(label=self.no_runner_label)
        self._add_notebook_tab(game_sw, "Game options")

    def _build_runner_tab(self, config_level):
        if self.runner_name:
            self.runner_box = RunnerBox(self.lutris_config)
            runner_sw = self.build_scrolled_window(self.runner_box)
        else:
            runner_sw = Gtk.Label(label=self.no_runner_label)
        self._add_notebook_tab(runner_sw, "Runner options")

    def _build_system_tab(self, config_level):
        self.system_box = SystemBox(self.lutris_config)
        self.system_sw = self.build_scrolled_window(self.system_box)
        self._add_notebook_tab(self.system_sw, "System options")

    def _add_notebook_tab(self, widget, label):
        self.notebook.append_page(widget, Gtk.Label(label=label))

    def build_action_area(self, button_callback, callback2=None):
        self.action_area.set_layout(Gtk.ButtonBoxStyle.EDGE)

        # Advanced settings checkbox
        checkbox = Gtk.CheckButton(label="Show advanced options")
        value = settings.read_setting("show_advanced_options")
        if value == "True":
            checkbox.set_active(value)
        checkbox.connect("toggled", self.on_show_advanced_options_toggled)
        self.action_area.pack_start(checkbox, False, False, 5)

        # Buttons
        hbox = Gtk.Box()
        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", self.on_cancel_clicked)
        hbox.pack_start(cancel_button, True, True, 10)

        save_button = Gtk.Button(label="Save")
        if callback2:
            save_button.connect("clicked", button_callback, callback2)
        else:
            save_button.connect("clicked", button_callback)
        hbox.pack_start(save_button, True, True, 0)
        self.action_area.pack_start(hbox, True, True, 0)

    def on_show_advanced_options_toggled(self, checkbox):
        value = True if checkbox.get_active() else False
        settings.write_setting("show_advanced_options", value)

        self._set_advanced_options_visible(value)

    def _set_advanced_options_visible(self, value):
        """Change visibility of advanced options across all config tabs."""
        widgets = self.system_box.get_children()
        if self.runner_name:
            widgets += self.runner_box.get_children()
        if self.game:
            widgets += self.game_box.get_children()

        for widget in widgets:
            if widget.get_style_context().has_class("advanced"):
                widget.set_visible(value)
                if value:
                    widget.set_no_show_all(not value)
                    widget.show_all()

    def on_runner_changed(self, widget):
        """Action called when runner drop down is changed."""
        runner_index = widget.get_active()
        current_page = self.notebook.get_current_page()

        if runner_index == 0:
            self.runner_name = None
            self.lutris_config = LutrisConfig()
        else:
            self.runner_name = widget.get_model()[runner_index][1]
            self.lutris_config = LutrisConfig(
                runner_slug=self.runner_name,
                game_config_id=self.game_config_id,
                level="game",
            )

        self._rebuild_tabs()
        self.notebook.set_current_page(current_page)

    def _rebuild_tabs(self):
        for i in range(self.notebook.get_n_pages(), 1, -1):
            self.notebook.remove_page(i - 1)
        self._build_game_tab()
        self._build_runner_tab("game")
        self._build_system_tab("game")
        self.show_all()

    def on_cancel_clicked(self, _widget=None, _event=None):
        """Dialog destroy callback."""
        if self.game:
            self.game.load_config()
        self.destroy()

    def is_valid(self):
        name = self.name_entry.get_text()
        if not self.runner_name:
            ErrorDialog("Runner not provided")
            return False
        if not name:
            ErrorDialog("Please fill in the name")
            return False
        if (
            self.runner_name in ("steam", "winesteam")
            and self.lutris_config.game_config.get("appid") is None
        ):
            ErrorDialog("Steam AppId not provided")
            return False
        return True

    def on_save(self, _button, callback=None):
        """Save game info and destroy widget. Return True if success."""
        if not self.is_valid():
            return False
        name = self.name_entry.get_text()

        if not self.slug:
            self.slug = slugify(name)

        if not self.game:
            self.game = Game()

        year = None
        if self.year_entry.get_text():
            year = int(self.year_entry.get_text())

        if self.lutris_config.game_config_id == TEMP_CONFIG:
            self.lutris_config.game_config_id = self.get_config_id()

        # Delete the old copy of the game if the runner changes
        runner_class = runners.import_runner(self.runner_name)
        runner = runner_class(self.lutris_config)
        if self.game.id and self.game.platform != runner.get_platform():
            self.game.remove()
        self.game.runner_name = self.runner_name

        self.game.name = name
        self.game.slug = self.slug
        self.game.year = year
        self.game.game_config_id = self.lutris_config.game_config_id
        self.game.runner_name = self.runner_name
        self.game.directory = runner.game_path
        self.game.is_installed = True
        if self.runner_name in ("steam", "winesteam"):
            self.game.steamid = self.lutris_config.game_config["appid"]

        fps_limit = self.game.config.system_config.get("fps_limit", None)
        if fps_limit:
            try:
                int(fps_limit)
            except ValueError:
                ErrorDialog("Fps limit only accept numbers")
                return

        self.game.set_platform_from_runner()
        self.game.save()
        self.game.load_config()
        self.destroy()
        self.saved = True
        if callback:
            callback()

    def on_custom_image_select(self, widget, image_type):
        dialog = Gtk.FileChooserDialog(
            "Please choose a custom image",
            self,
            Gtk.FileChooserAction.OPEN,
            (
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN,
                Gtk.ResponseType.OK,
            ),
        )

        image_filter = Gtk.FileFilter()
        image_filter.set_name("Images")
        image_filter.add_pixbuf_formats()
        dialog.add_filter(image_filter)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            image_path = dialog.get_filename()
            if image_type == "banner":
                self.game.has_custom_banner = True
                dest_path = datapath.get_banner_path(self.game.slug)
                size = BANNER_SIZE
                file_format = "jpeg"
            else:
                self.game.has_custom_icon = True
                dest_path = datapath.get_icon_path(self.game.slug)
                size = ICON_SIZE
                file_format = "png"
            pixbuf = get_pixbuf(image_path, size)
            pixbuf.savev(dest_path, file_format, [], [])
            self._set_image(image_type)

            if image_type == "icon":
                resources.udpate_desktop_icons()

        dialog.destroy()

    def on_custom_image_reset_clicked(self, widget, image_type):
        if image_type == "banner":
            self.game.has_custom_banner = False
            dest_path = datapath.get_banner_path(self.game.slug)
        elif image_type == "icon":
            self.game.has_custom_icon = False
            dest_path = datapath.get_icon_path(self.game.slug)
        else:
            raise ValueError("Unsupported image type %s", image_type)
        os.remove(dest_path)
        self._set_image(image_type)
