#!/usr/bin/env python3

import ast
import hashlib
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import urllib.request
import urllib.error
import importlib.util
from datetime import datetime
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, scrolledtext
from queue import Queue

# Try to import optional theme library
try:
    from ttkthemes import ThemedTk
except ImportError:
    ThemedTk = None

# Try to import optional YAML library
try:
    import yaml
except ImportError:
    yaml = None


class ProgressDialog:
    """Custom progress dialog with better UX"""
    def __init__(self, parent, title="Processing", message="Please wait..."):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (150 // 2)
        self.dialog.geometry(f"400x150+{x}+{y}")

        self.message_label = ttk.Label(self.dialog, text=message, font=('Inter', 10))
        self.message_label.pack(pady=20)

        self.progress = ttk.Progressbar(self.dialog, mode='indeterminate', length=300)
        self.progress.pack(pady=10)
        self.progress.start()

        self.cancel_button = ttk.Button(self.dialog, text="Cancel", command=self.cancel)
        self.cancel_button.pack(pady=10)

        self.cancelled = False

    def update_message(self, message):
        self.message_label.config(text=message)
        self.dialog.update_idletasks()

    def cancel(self):
        self.cancelled = True
        self.close()

    def close(self):
        self.progress.stop()
        self.dialog.destroy()


class FlatpakBuilder:
    def __init__(self, root):
        self.root = root
        self._initialize_variables()
        self._setup_logging()
        self._configure_window()
        self._load_initial_data()
        self._detect_system_info()
        self._build_ui()
        self._bind_events()
        self.setup_autosave()
        self.logger.info("Application initialized successfully.")

    # ===================================================================================
    # UI Construction
    # ===================================================================================

    def _build_ui(self):
        """Construct the entire user interface from scratch."""
        self._setup_styles()
        self._create_menubar()
        self._create_main_layout()
        self._create_statusbar()

    def _setup_styles(self):
        """Configure all ttk styles in one place."""
        style = ttk.Style(self.root)
        if ThemedTk:
            try:
                self.root.set_theme("arc")
                self.logger.info("Applied 'arc' theme.")
            except tk.TclError:
                self.logger.warning("Failed to apply 'arc' theme, falling back to default.")

        font_normal = ('Inter', 10)
        font_bold = ('Inter', 10, 'bold')
        font_title = ('Inter', 16, 'bold')
        font_heading = ('Inter', 11, 'bold')
        font_mono = ('monospace', 9)
        font_small = ('Inter', 9)

        style.configure('TLabel', font=font_normal)
        style.configure('Title.TLabel', font=font_title)
        style.configure('Heading.TLabel', font=font_heading)
        style.configure('TButton', font=font_normal)
        style.configure('Accent.TButton', font=font_bold)
        style.configure('Placeholder.TEntry', foreground='#95a5a6')
        style.configure('Error.TLabel', foreground='#e74c3c', font=font_small)
        style.configure('TNotebook.Tab', font=font_bold, padding=[10, 5])
        style.configure('TLabelframe.Label', font=font_bold)

        bg_color = style.lookup('TFrame', 'background')
        fg_color = style.lookup('TLabel', 'foreground')
        self.output_text_config = {'background': bg_color, 'foreground': fg_color, 'font': font_mono, 'relief': 'solid', 'bd': 1}


    def _create_menubar(self):
        """Create the main application menu bar."""
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New Project", command=self.new_project, accelerator="Ctrl+N")
        filemenu.add_separator()
        filemenu.add_command(label="Save Configuration", command=self.save_configuration, accelerator="Ctrl+S")
        filemenu.add_command(label="Load Configuration", command=self.load_configuration, accelerator="Ctrl+O")
        filemenu.add_separator()
        filemenu.add_command(label="Export Manifest Only", command=self.export_manifest_only)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.on_closing, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=filemenu)

        toolsmenu = tk.Menu(menubar, tearoff=0)
        toolsmenu.add_command(label="Validate Configuration", command=self.validate_configuration)
        toolsmenu.add_command(label="Refresh Runtime List", command=self.refresh_runtime_list)
        toolsmenu.add_separator()
        testmenu = tk.Menu(toolsmenu, tearoff=0)
        testmenu.add_command(label="Run Application", command=self.run_flatpak_app)
        testmenu.add_command(label="Run with Terminal", command=lambda: self.run_flatpak_app(with_terminal=True))
        testmenu.add_separator()
        testmenu.add_command(label="Show Sandbox Info", command=self.show_sandbox_info)
        testmenu.add_command(label="Show Permissions", command=self.show_permissions_info)
        testmenu.add_command(label="Show Sandbox Filesystem", command=self.show_sandbox_filesystem)
        testmenu.add_separator()
        testmenu.add_command(label="Clean Application Data", command=self.clean_app_data)
        toolsmenu.add_cascade(label="Test Application", menu=testmenu)
        toolsmenu.add_separator()
        sdkmenu = tk.Menu(toolsmenu, tearoff=0)
        sdkmenu.add_command(label="Update SDK Cache", command=self._refresh_sdk_cache)
        sdkmenu.add_command(label="Show Available SDKs", command=self.show_available_sdks)
        sdkmenu.add_command(label="Manage Installed SDKs", command=self.manage_sdks)
        toolsmenu.add_cascade(label="SDK Management", menu=sdkmenu)
        menubar.add_cascade(label="Tools", menu=toolsmenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", command=self.show_about)
        helpmenu.add_command(label="Flatpak Documentation", command=self.open_flatpak_docs)
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.root.config(menu=menubar)

    def _create_main_layout(self):
        """Create the main window layout with notebook and action buttons."""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(header_frame, text="Flatpak Manifest Generator", style='Title.TLabel').pack()
        ttk.Label(header_frame, text="Create professional Flatpak applications with ease").pack()

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky="nsew", pady=5)
        self._create_basic_info_tab()
        self._create_build_config_tab()
        self._create_dependencies_tab()
        self._create_permissions_tab()
        self._create_build_output_tab()
        self._create_action_buttons(main_frame)

        footer_frame = ttk.Frame(main_frame)
        footer_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(footer_frame, text="Created with ❤️ by Grouvya!", font=("Inter", 9)).pack(side=tk.LEFT)
        ttk.Button(footer_frame, text="Support Creator", command=self.open_donation_link).pack(side=tk.RIGHT)

    def _create_action_buttons(self, parent):
        """Create the main action buttons (Validate, Generate, Build)."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        button_frame.columnconfigure((0, 1, 2), weight=1)
        self.validate_button = ttk.Button(button_frame, text="Validate", command=self.validate_configuration)
        self.validate_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.generate_button = ttk.Button(button_frame, text="Generate Files", command=self.generate_files)
        self.generate_button.grid(row=0, column=1, sticky="ew", padx=5)
        self.build_button = ttk.Button(button_frame, text="Build & Install", command=self.start_build_process, style='Accent.TButton')
        self.build_button.grid(row=0, column=2, sticky="ew", padx=(5, 0))

    def _create_statusbar(self):
        """Create the bottom status bar."""
        self.status_frame = ttk.Frame(self.root, padding=(5, 2))
        self.status_frame.grid(row=1, column=0, sticky="ew")
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT, padx=5)
        self.progress_bar = ttk.Progressbar(self.status_frame, orient='horizontal', length=150, mode='indeterminate')
        self.progress_bar.pack(side=tk.RIGHT, padx=5)

    def _create_form_row(self, parent, row_index, label_text, widget, help_text=None):
        """Helper to create a standard Label + Widget form row."""
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row_index, column=0, sticky="nw", padx=5, pady=5)
        widget_frame = ttk.Frame(parent)
        widget_frame.grid(row=row_index, column=1, sticky="ew", padx=5, pady=5)
        widget_frame.columnconfigure(0, weight=1)
        widget.grid(row=0, column=0, sticky="ew")
        if help_text:
            help_label = ttk.Label(widget_frame, text=help_text, font=('Inter', 9), foreground='#555')
            help_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        return widget_frame

    def _create_basic_info_tab(self):
        """Build the 'Basic Info' tab."""
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="👤 Basic Info")
        tab.columnconfigure(0, weight=1)
        app_section = ttk.LabelFrame(tab, text="Application Identity", padding=10)
        app_section.grid(row=0, column=0, sticky="ew")
        app_section.columnconfigure(1, weight=1)

        app_id_frame = ttk.Frame(app_section)
        self.app_id_entry = ttk.Entry(app_id_frame)
        self.add_placeholder(self.app_id_entry, "e.g., io.github.username.appname")
        self.fields["appId"] = self.app_id_entry
        self.app_id_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        ttk.Button(app_id_frame, text="Generate", command=self.generate_app_id).pack(side=tk.LEFT)
        self._create_form_row(app_section, 0, "App ID:*", app_id_frame)
        self.app_id_error = ttk.Label(app_section, text="", style='Error.TLabel')
        self.app_id_error.grid(row=1, column=1, sticky="w", padx=5)
        self.validation_errors["appId"] = self.app_id_error

        self.create_entry_with_validation(app_section, 2, "App Name:*", "appName", "e.g., My Awesome Application", required=True)
        self.create_entry_with_validation(app_section, 3, "Author:*", "author", "Your name or organization", required=True)
        self.create_entry_with_validation(app_section, 4, "Summary:*", "summary", "A short, descriptive one-line summary", required=True)

        meta_section = ttk.LabelFrame(tab, text="Metadata", padding=10)
        meta_section.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        meta_section.columnconfigure(1, weight=1)
        self.create_icon_selector(meta_section, 0, "Icon File:")
        categories = ["AudioVideo", "Development", "Education", "Game", "Graphics", "Network", "Office", "Science", "System", "Utility"]
        self.create_combobox(meta_section, 1, "Primary Category:", "category", categories)

    def _create_build_config_tab(self):
        """Build the 'Build Config' tab."""
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="🔧 Build Config")
        tab.columnconfigure(0, weight=1)
        platform_section = ttk.LabelFrame(tab, text="Platform Configuration", padding=10)
        platform_section.grid(row=0, column=0, sticky="ew")
        platform_section.columnconfigure(1, weight=1)

        runtime_combo = self.create_combobox(platform_section, 0, "Runtime:*", "runtime", self.get_available_runtimes(), required=True)
        runtime_combo.bind("<<ComboboxSelected>>", self.on_runtime_selected)
        self.create_combobox(platform_section, 1, "Runtime Version:*", "runtimeVersion", [], readonly=False, required=True)
        sdk_combo = self.create_combobox(platform_section, 2, "SDK:*", "sdk", self.get_available_sdks(), required=True)
        sdk_combo.bind("<<ComboboxSelected>>", self.on_sdk_selected)
        self.create_combobox(platform_section, 3, "SDK Version:*", "sdkVersion", [], readonly=False, required=True)

        source_section = ttk.LabelFrame(tab, text="Source Configuration", padding=10)
        source_section.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        source_section.columnconfigure(1, weight=1)
        source_type_frame = ttk.Frame(source_section)
        ttk.Radiobutton(source_type_frame, text="Directory", variable=self.source_type, value="directory", command=self.update_source_ui).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(source_type_frame, text="Archive", variable=self.source_type, value="archive", command=self.update_source_ui).pack(side=tk.LEFT)
        self._create_form_row(source_section, 0, "Source Type:*", source_type_frame)
        self.create_source_selector(source_section, 1, "Source Location:*")
        self.sha_frame = ttk.Frame(source_section)
        ttk.Label(self.sha_frame, text="SHA256:", style='TLabel').pack(side=tk.LEFT, padx=5)
        ttk.Label(self.sha_frame, textvariable=self.source_file_sha256, style='TLabel', font=('Courier', 9)).pack(side=tk.LEFT, padx=5)
        self.executable_row = 2
        self.create_executable_selector(source_section)
        build_systems = ["simple", "meson", "cmake-ninja", "autotools", "qmake"]
        self.create_combobox(source_section, self.executable_row + 1, "Build System:", "buildSystem", build_systems)

    def _create_dependencies_tab(self):
        """Build the 'Dependencies' tab."""
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="📦 Dependencies")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        main_pane = ttk.PanedWindow(tab, orient=tk.VERTICAL)
        main_pane.grid(row=0, column=0, sticky="nsew")

        python_frame = ttk.Frame(main_pane)
        main_pane.add(python_frame, weight=3)
        python_frame.columnconfigure(0, weight=1)
        python_frame.rowconfigure(0, weight=1)
        py_section = ttk.LabelFrame(python_frame, text="Python Dependencies (from requirements.txt)", padding=10)
        py_section.grid(row=0, column=0, sticky="nsew")
        py_section.columnconfigure(0, weight=1)
        py_section.rowconfigure(1, weight=1)
        py_controls = ttk.Frame(py_section)
        py_controls.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        py_controls.columnconfigure((0, 1), weight=1)
        self.generate_deps_button = ttk.Button(py_controls, text="Auto-Generate Dependencies", command=self.run_dependency_generator, state=tk.DISABLED)
        self.generate_deps_button.grid(row=0, column=0, sticky="ew", padx=(0,5))
        self.validate_deps_button = ttk.Button(py_controls, text="Validate Dependencies", command=self.validate_dependencies)
        self.validate_deps_button.grid(row=0, column=1, sticky="ew", padx=(5,0))

        deps_config = self.output_text_config.copy()
        deps_config.pop('font', None)
        self.fields["dependencies"] = scrolledtext.ScrolledText(py_section, height=10, font=('Courier', 9), wrap='none', **deps_config)
        self.fields["dependencies"].grid(row=1, column=0, sticky="nsew")

        system_frame = ttk.Frame(main_pane)
        main_pane.add(system_frame, weight=1)
        system_frame.columnconfigure(0, weight=1)
        system_frame.rowconfigure(0, weight=1)
        sys_section = ttk.LabelFrame(system_frame, text="System Dependencies", padding=10)
        sys_section.grid(row=0, column=0, sticky="nsew")
        sys_section.columnconfigure(0, weight=1)
        sys_section.rowconfigure(1, weight=1)
        ttk.Label(sys_section, text="Additional SDK packages (one per line):").grid(row=0, column=0, sticky="w")
        self.fields["systemDeps"] = scrolledtext.ScrolledText(sys_section, height=4, font=('Courier', 9), **deps_config)
        self.fields["systemDeps"].grid(row=1, column=0, sticky="nsew", pady=5)

    def _create_permissions_tab(self):
        """Build the 'Permissions' tab."""
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="🔒 Permissions")
        tab.columnconfigure(0, weight=1)

        groups = {
            "Filesystem Access": [("home", "Home directory (--filesystem=home)"), ("host", "Host filesystem (--filesystem=host)"),],
            "Devices & Hardware": [("dri", "GPU acceleration (--device=dri)", True), ("usb", "USB devices (--device=all)"), ("pulseaudio", "Audio access (--socket=pulseaudio)"),],
            "Network & Communication": [("network", "Network access (--share=network)", True),],
            "Display Server": [("x11", "X11 display (--socket=x11)", True), ("wayland", "Wayland display (--socket=wayland)", True),],
        }

        row_count = 0
        for title, perms in groups.items():
            section = ttk.LabelFrame(tab, text=title, padding=10)
            section.grid(row=row_count, column=0, sticky="ew", pady=(0, 10))
            row_count += 1
            for i, perm_info in enumerate(perms):
                key, text = perm_info[0], perm_info[1]
                default_state = perm_info[2] if len(perm_info) > 2 else False
                self.finish_args_vars[key] = tk.BooleanVar(value=default_state)
                ttk.Checkbutton(section, text=text, variable=self.finish_args_vars[key]).pack(anchor="w", padx=5, pady=2)

        custom_section = ttk.LabelFrame(tab, text="Custom Permissions", padding=10)
        custom_section.grid(row=row_count, column=0, sticky="ew", pady=(0, 10))
        custom_section.columnconfigure(0, weight=1)
        custom_section.rowconfigure(1, weight=1)
        ttk.Label(custom_section, text="Additional finish-args (one per line):").grid(row=0, column=0, sticky="w")

        custom_perms_config = self.output_text_config.copy()
        custom_perms_config.pop('font', None)
        self.fields["customPerms"] = scrolledtext.ScrolledText(custom_section, height=4, font=('Courier', 9), **custom_perms_config)
        self.fields["customPerms"].grid(row=1, column=0, sticky="nsew", pady=5)

    def _create_build_output_tab(self):
        """Build the 'Build Output' tab."""
        self.output_frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.output_frame, text="⚙️ Build Output")
        self.output_frame.columnconfigure(0, weight=1)
        self.output_frame.rowconfigure(1, weight=1)

        controls_frame = ttk.Frame(self.output_frame)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.copy_command_button = ttk.Button(controls_frame, text="📋 Copy Last Command", command=self.copy_build_command, state="disabled")
        self.copy_command_button.pack(side=tk.LEFT)

        self.output_text = scrolledtext.ScrolledText(self.output_frame, wrap=tk.WORD, state='disabled', **self.output_text_config)
        self.output_text.grid(row=1, column=0, sticky="nsew")

        self.output_text.tag_config('INFO', foreground='blue')
        self.output_text.tag_config('ERROR', foreground='red', font=("monospace", 9, "bold"))
        self.output_text.tag_config('SUCCESS', foreground='green')
        self.output_text.tag_config('CMD', foreground='#555555', lmargin1=10, lmargin2=10)

    # ===================================================================================
    # Backend and Helper Methods
    # ===================================================================================

    def _find_executable(self, name):
        """Finds an executable, checking standard system, user, and venv paths."""
        path = shutil.which(name)
        if path:
            self.logger.info(f"Found '{name}' at '{path}' via shutil.which.")
            return path

        try:
            python_dir = Path(sys.executable).parent
            relative_path = python_dir / name
            if relative_path.is_file() and os.access(relative_path, os.X_OK):
                self.logger.info(f"Found '{name}' relative to Python interpreter at '{relative_path}'.")
                return str(relative_path)
        except Exception:
            pass

        user_path = Path.home() / ".local" / "bin" / name
        if user_path.is_file() and os.access(user_path, os.X_OK):
            self.logger.info(f"Found '{name}' at user path '{user_path}'.")
            return str(user_path)

        for p in ["/usr/bin", "/bin", "/usr/local/bin"]:
            sys_path = Path(p) / name
            if sys_path.is_file() and os.access(sys_path, os.X_OK):
                self.logger.info(f"Found '{name}' at system path '{sys_path}'.")
                return str(sys_path)

        self.logger.warning(f"Could not find executable '{name}' in PATH or common locations.")
        return None

    def _initialize_variables(self):
        self.logger = logging.getLogger(__name__)
        self.debug_mode = os.environ.get('FLATPAK_BUILDER_DEBUG', '0') == '1'
        self.placeholders = {}
        self.fields = {}
        self.validation_errors = {}
        self.finish_args_vars = {}
        self.source_path = tk.StringVar()
        self.source_file_sha256 = tk.StringVar(value="Not calculated")
        self.icon_file_path = tk.StringVar()
        self.source_type = tk.StringVar(value="directory")
        self.status_var = tk.StringVar(value="Ready")
        self.config_dir = Path.home() / '.flatpak-generator'
        self.default_save_dir = self.config_dir / 'saves'
        self.backup_dir = self.config_dir / 'backups'
        self.sdk_cache_dir = self.config_dir / 'sdk_cache'
        self.sdk_cache_file = self.sdk_cache_dir / 'sdk_info.json'
        self.recent_saves_file = self.config_dir / 'recent_saves.json'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.default_save_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        self.sdk_cache_dir.mkdir(exist_ok=True)
        self.installed_runtimes = {}
        self.installed_sdks = {}
        self.sdk_cache = {'last_update': 0, 'sdks': {}}
        self.sdk_cache_timeout = 3600
        self.recent_save_locations = []
        self.last_save_time = None
        self.unsaved_changes = False
        self.last_yml_path = None
        self.last_build_command = ""
        self._temp_files = set()
        self._running_threads = set()
        self._active_dialogs = set()
        self._running_process = None
        self.output_queue = Queue()
        self.autosave_interval = 300000
        self.VERSION_MAP = {
            "org.gnome.Platform": ["47", "46", "45", "44"],
            "org.gnome.Sdk": ["47", "46", "45", "44"],
            "org.kde.Platform": ["6.8", "6.7", "6.6"],
            "org.kde.Sdk": ["6.8", "6.7", "6.6"],
            "org.freedesktop.Platform": ["23.08", "22.08"],
            "org.freedesktop.Sdk": ["23.08", "22.08"]
        }

    def _setup_logging(self):
        log_dir = Path(tempfile.gettempdir()) / 'flatpak-generator'
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f'generator-{datetime.now():%Y%m%d-%H%M%S}.log'
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO if not self.debug_mode else logging.DEBUG)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        sys.excepthook = self.handle_global_error
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _configure_window(self):
        self.root.title("Flatpak Manifest Generator v2.5")
        self.root.minsize(900, 700)
        self.center_window(1100, 800)

    def _load_initial_data(self):
        self.recent_save_locations = self._load_recent_saves()
        self._load_sdk_cache()

    def _detect_system_info(self):
        self.system_arch = self._detect_system_arch()
        self.logger.info(f'Detected system architecture: {self.system_arch}')
        self.installed_runtimes, self.installed_sdks = self.detect_installed_refs()

    def on_closing(self):
        if self.unsaved_changes and messagebox.askyesno("Quit", "You have unsaved changes. Are you sure you want to quit?"):
            self.cleanup_resources()
            self.root.destroy()
        elif not self.unsaved_changes:
            self.cleanup_resources()
            self.root.destroy()

    def _detect_system_arch(self):
        arch_map = {'x86_64': 'x86_64', 'amd64': 'x86_64', 'aarch64': 'aarch64', 'arm64': 'aarch64', 'armv8l': 'aarch64', 'armv7l': 'arm', 'i686': 'x86_32'}
        try:
            return arch_map.get(platform.machine(), platform.machine())
        except Exception as e:
            self.logger.warning(f'Failed to detect architecture: {e}')
            return 'x86_64'

    def _bind_events(self):
        self.root.bind('<Control-n>', lambda e: self.new_project())
        self.root.bind('<Control-s>', lambda e: self.save_configuration())
        self.root.bind('<Control-o>', lambda e: self.load_configuration())
        self.root.bind('<Control-q>', lambda e: self.on_closing())
        self.root.bind('<F5>', lambda e: self.refresh_runtime_list())
        for widget in self.fields.values():
            if isinstance(widget, (ttk.Entry, ttk.Combobox, scrolledtext.ScrolledText)):
                widget.bind('<KeyRelease>', self._set_unsaved_changes)
        for var in self.finish_args_vars.values():
            var.trace_add('write', self._set_unsaved_changes)

    def _set_unsaved_changes(self, *args):
        self.unsaved_changes = True
        self.status_var.set("Unsaved changes")

    def center_window(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def copy_build_command(self):
        if self.last_build_command:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.last_build_command)
            self.update_status("Build command copied to clipboard.")
        else:
            self.update_status("No build command to copy yet.")

    def create_entry_with_validation(self, parent, row, label_text, key, placeholder="", required=False):
        ttk.Label(parent, text=label_text, style='Heading.TLabel' if required else 'TLabel').grid(row=row, column=0, sticky="nw", padx=5, pady=5)
        entry_frame = ttk.Frame(parent)
        entry_frame.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
        entry_frame.columnconfigure(0, weight=1)
        entry = ttk.Entry(entry_frame)
        entry.grid(row=0, column=0, sticky="ew")
        self.fields[key] = entry
        if placeholder:
            self.add_placeholder(entry, placeholder)
        error_label = ttk.Label(entry_frame, text="", style='Error.TLabel')
        error_label.grid(row=1, column=0, sticky="w")
        self.validation_errors[key] = error_label
        if required:
            entry.bind('<FocusOut>', lambda e, k=key: self.validate_field(k, required=True))
            entry.bind('<KeyRelease>', lambda e, k=key: self.validate_field(k, required=True))

    def create_combobox(self, parent, row, label_text, key, values, readonly=True, required=False):
        ttk.Label(parent, text=label_text, style='Heading.TLabel' if required else 'TLabel').grid(row=row, column=0, sticky="nw", padx=5, pady=5)
        combo_frame = ttk.Frame(parent)
        combo_frame.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
        combo_frame.columnconfigure(0, weight=1)
        combo = ttk.Combobox(combo_frame, values=values, state="readonly" if readonly else "normal")
        combo.grid(row=0, column=0, sticky="ew")
        if values:
            combo.set(values[0])
        self.fields[key] = combo
        if required:
            error_label = ttk.Label(combo_frame, text="", style='Error.TLabel')
            error_label.grid(row=1, column=0, sticky="w")
            self.validation_errors[key] = error_label
            combo.bind('<<ComboboxSelected>>', lambda e, k=key: self.validate_field(k, required=True))
        return combo

    def create_source_selector(self, parent, row, label_text):
        self.source_selector_label = ttk.Label(parent, text=label_text, style='Heading.TLabel')
        self.source_selector_label.grid(row=row, column=0, sticky="nw", padx=5, pady=5)
        source_frame = ttk.Frame(parent)
        source_frame.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
        source_frame.columnconfigure(0, weight=1)
        path_frame = ttk.Frame(source_frame)
        path_frame.grid(row=0, column=0, sticky="ew")
        path_frame.columnconfigure(0, weight=1)
        self.source_entry = ttk.Entry(path_frame, textvariable=self.source_path, state="readonly")
        self.source_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.source_selector_button = ttk.Button(path_frame, text="Browse...", command=self.select_source_directory)
        self.source_selector_button.grid(row=0, column=1)
        self.source_info_label = ttk.Label(source_frame, text="", style='TLabel', font=('Inter', 9))
        self.source_info_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

    def create_icon_selector(self, parent, row, label_text):
        ttk.Label(parent, text=label_text, style='TLabel').grid(row=row, column=0, sticky="nw", padx=5, pady=5)
        icon_frame = ttk.Frame(parent)
        icon_frame.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
        icon_frame.columnconfigure(0, weight=1)
        path_frame = ttk.Frame(icon_frame)
        path_frame.grid(row=0, column=0, sticky="ew")
        path_frame.columnconfigure(0, weight=1)
        ttk.Entry(path_frame, textvariable=self.icon_file_path, state="readonly").grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(path_frame, text="Browse...", command=self.select_icon_file).grid(row=0, column=1)
        self.icon_info_label = ttk.Label(icon_frame, text="Recommended: 128x128 PNG or SVG", style='TLabel', font=('Inter', 9))
        self.icon_info_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

    def create_executable_selector(self, parent):
        self.executable_label = ttk.Label(parent, text="Main Executable:", style='TLabel')
        self.executable_label.grid(row=self.executable_row, column=0, sticky="nw", padx=5, pady=5)
        self.executable_frame = ttk.Frame(parent)
        self.executable_frame.grid(row=self.executable_row, column=1, sticky="ew", padx=5, pady=5)
        self.executable_frame.columnconfigure(0, weight=1)
        exec_path_frame = ttk.Frame(self.executable_frame)
        exec_path_frame.pack(fill=tk.X)
        exec_path_frame.columnconfigure(0, weight=1)
        self.executable_entry = ttk.Entry(exec_path_frame)
        self.add_placeholder(self.executable_entry, "e.g., main.py or my-binary")
        self.executable_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.fields["executable"] = self.executable_entry
        self.executable_button = ttk.Button(exec_path_frame, text="Browse...", command=self.select_executable_file)
        self.executable_button.grid(row=0, column=1)
        self.autodetect_button = ttk.Button(self.executable_frame, text="Auto-detect", command=self.autodetect_executable)
        self.autodetect_button.pack(side=tk.LEFT, pady=(5,0))

    def add_placeholder(self, entry, placeholder):
        self.placeholders[entry] = placeholder
        entry.insert(0, placeholder)
        entry.configure(style='Placeholder.TEntry')
        entry.bind('<FocusIn>', self.on_focus_in)
        entry.bind('<FocusOut>', self.on_focus_out)

    def on_focus_in(self, event):
        widget = event.widget
        placeholder = self.placeholders.get(widget)
        if placeholder and widget.get() == placeholder:
            widget.delete(0, "end")
            widget.configure(style='TEntry')

    def on_focus_out(self, event):
        widget = event.widget
        placeholder = self.placeholders.get(widget)
        if placeholder and not widget.get().strip():
            widget.delete(0, "end")
            widget.insert(0, placeholder)
            widget.configure(style='Placeholder.TEntry')

    def install_flatpak_sdk(self, sdk, version, on_complete_callback):
        try:
            remotes_output = subprocess.check_output(['flatpak', 'remotes', '--columns=name'], text=True, stderr=subprocess.PIPE)
            if 'flathub' not in remotes_output.split():
                message = "The 'flathub' remote is not configured. Please add it by running:\n\nflatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo"
                self._append_output(f"\nERROR: {message}\n", "ERROR")
                messagebox.showerror("Prerequisite Missing", message)
                on_complete_callback(False)
                return
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            message = f"Failed to check for Flatpak remotes: {e}"
            self._append_output(f"\nERROR: {message}\n", "ERROR")
            messagebox.showerror("Error", message)
            on_complete_callback(False)
            return

        command = ['flatpak', '--user', 'install', '--assumeyes', 'flathub', f"{sdk}//{version}"]
        self.notebook.select(self.output_frame)
        self._clear_output()
        self._append_output(f"Attempting to install required SDK:\n{' '.join(command)}\n\n", "CMD")

        def on_install_done(return_code):
            if return_code == 0:
                self._append_output("\nSDK installed successfully.\n", "SUCCESS")
                on_complete_callback(True)
            else:
                error_message = f"SDK installation failed with exit code {return_code}."
                self._append_output(f"\n{error_message}\n", "ERROR")
                messagebox.showerror("Installation Failed",
                    f"{error_message}\n\n"
                    "Common causes:\n"
                    "• No internet connection.\n"
                    "• The SDK version may not exist on Flathub.\n"
                    "• Insufficient disk space.\n\n"
                    "Please check the output in the 'Build Output' tab for more details.")
                on_complete_callback(False)

        self._run_command_in_thread(command, on_complete=on_install_done)

    def _validate_sdk_installation(self, sdk, sdk_version, on_valid_callback):
        try:
            result = subprocess.run(['flatpak', 'list', '--runtime', '--columns=ref'], capture_output=True, text=True, check=True)
            sdk_ref = f"{sdk}/{self.system_arch}/{sdk_version}"

            if any(sdk_ref in line for line in result.stdout.splitlines()):
                on_valid_callback()
                return

            if messagebox.askyesno("SDK Not Found", f"The required SDK '{sdk}' version '{sdk_version}' is not installed.\n\nWould you like to install it now from Flathub?"):
                def post_install_check(success):
                    if success:
                        on_valid_callback()
                    else:
                        self.logger.warning("SDK installation was unsuccessful. Aborting build.")
                self.install_flatpak_sdk(sdk, sdk_version, on_complete_callback=post_install_check)
            else:
                messagebox.showinfo("Build Canceled", "The required SDK is not installed. Build process canceled.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check SDK installation: {e}")

    def validate_field(self, field_key, required=False):
        value = self.get_field_value(field_key)
        error_label = self.validation_errors.get(field_key)
        if not error_label: return True
        if required and not value:
            error_label.config(text="This field is required")
            return False
        if field_key == "appId" and value and not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*){2,}$', value):
            error_label.config(text="Invalid App ID format. e.g.: com.example.app")
            return False
        error_label.config(text="")
        return True

    def detect_installed_refs(self):
        runtimes, sdks = {}, {}
        try:
            result = subprocess.run(['flatpak', 'list', '--runtime', '--columns=application,branch'], check=True, capture_output=True, text=True, timeout=10)
            for line in result.stdout.strip().split('\n'):
                ref, branch = line.split('\t')
                if ref.endswith(".Sdk"):
                    sdks.setdefault(ref, set()).add(branch)
                elif ref.endswith(".Platform"):
                    runtimes.setdefault(ref, set()).add(branch)
        except Exception as e:
            self.logger.warning(f"Error detecting Flatpak refs: {e}")
        return {k: sorted(list(v), reverse=True) for k, v in runtimes.items()}, {k: sorted(list(v), reverse=True) for k, v in sdks.items()}

    def get_available_runtimes(self):
        return sorted(list(set(self.installed_runtimes.keys()) | set(self.VERSION_MAP.keys())))

    def get_available_sdks(self):
        return sorted(list(set(self.installed_sdks.keys()) | {k for k in self.VERSION_MAP if k.endswith('.Sdk')}))

    def _get_combined_versions(self, ref_name, installed_dict):
        versions = set(installed_dict.get(ref_name, [])) | set(self.VERSION_MAP.get(ref_name, []))
        return sorted(list(versions), reverse=True) if versions else ['23.08']

    def on_runtime_selected(self, event=None):
        try:
            selected_runtime = self.fields["runtime"].get()
            corresponding_sdk = selected_runtime.replace("Platform", "Sdk")
            sdk_combo = self.fields.get("sdk")
            if sdk_combo:
                sdk_options = self.get_available_sdks()
                sdk_combo['values'] = sdk_options
                if corresponding_sdk in sdk_options:
                    sdk_combo.set(corresponding_sdk)
                elif sdk_options:
                    sdk_combo.set(sdk_options[0])
            runtime_version_combo = self.fields.get("runtimeVersion")
            if runtime_version_combo:
                versions = self._get_combined_versions(selected_runtime, self.installed_runtimes)
                runtime_version_combo['values'] = versions
                if versions:
                    runtime_version_combo.set(versions[0])
            self.on_sdk_selected()
        except (KeyError, AttributeError): pass

    def on_sdk_selected(self, event=None):
        try:
            selected_sdk = self.fields["sdk"].get()
            sdk_version_combo = self.fields.get("sdkVersion")
            if not sdk_version_combo: return
            versions = self._get_combined_versions(selected_sdk, self.installed_sdks)
            sdk_version_combo['values'] = versions
            runtime_version = self.fields.get("runtimeVersion", tk.StringVar()).get()
            if runtime_version in versions:
                sdk_version_combo.set(runtime_version)
            elif versions:
                sdk_version_combo.set(versions[0])
        except (KeyError, AttributeError): pass

    def update_source_ui(self):
        is_archive = self.source_type.get() == "archive"
        self.source_selector_label.config(text="Source Archive:*" if is_archive else "Source Directory:*")
        self.source_selector_button.config(command=self.select_source_archive if is_archive else self.select_source_directory)
        if is_archive:
            self.executable_label.grid_remove()
            self.executable_frame.grid_remove()
            self.sha_frame.grid(row=self.executable_row - 1, column=1, sticky="ew", padx=5, pady=2)
        else:
            self.executable_label.grid(row=self.executable_row, column=0, sticky="nw", padx=5, pady=5)
            self.executable_frame.grid(row=self.executable_row, column=1, sticky="ew", padx=5, pady=5)
            self.sha_frame.grid_remove()
        self.source_path.set("")
        self.source_file_sha256.set("Not calculated")
        self.update_source_info()
        self.update_deps_buttons_state()

    def update_source_info(self):
        path = self.source_path.get()
        info = ""
        try:
            if os.path.isfile(path): info = f"File size: {self.format_file_size(os.path.getsize(path))}"
            elif os.path.isdir(path): info = f"Directory contains {sum(len(files) for _, _, files in os.walk(path))} files"
        except: pass
        self.source_info_label.config(text=info)

    def format_file_size(self, size_bytes):
        if size_bytes == 0: return "0 B"
        s = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < 4:
            size_bytes /= 1024
            i += 1
        return f"{size_bytes:.1f} {s[i]}"

    def update_deps_buttons_state(self):
        is_dir = self.source_type.get() == "directory" and os.path.isdir(self.source_path.get())
        self.generate_deps_button.config(state=tk.NORMAL if is_dir else tk.DISABLED)

    def get_field_value(self, key):
        widget = self.fields.get(key)
        if not widget: return ""
        try:
            value = widget.get("1.0", "end-1c").strip() if isinstance(widget, (tk.Text, scrolledtext.ScrolledText)) else widget.get().strip()
            return "" if self.placeholders.get(widget) == value else value
        except: return ""

    def update_status(self, message):
        try:
            self.status_var.set(message)
            self.root.update_idletasks()
        except tk.TclError: pass

    def select_source_directory(self):
        dirpath = filedialog.askdirectory(title="Select Source Directory")
        if dirpath:
            self.source_path.set(dirpath)
            self.update_source_info()
            self.update_deps_buttons_state()
        if not self.get_field_value('executable'):
            self.root.after(100, self.autodetect_executable)

    def select_source_archive(self):
        filepath = filedialog.askopenfilename(title="Select Source Archive", filetypes=[("Archives", "*.tar.gz;*.tar.bz2;*.tar.xz;*.zip"), ("All files", "*.*")])
        if filepath:
            self.source_path.set(filepath)
            self.update_source_info()
        self.update_status("Calculating SHA256...")
        self.progress_bar.start()
        threading.Thread(target=self._calculate_hash_thread, args=(filepath,), daemon=True).start()

    def _calculate_hash_thread(self, filepath):
        try:
            sha = self.calculate_sha256(filepath)
            self.root.after(0, lambda: [self.source_file_sha256.set(sha), self.update_status("Hash calculated")])
        except Exception as e:
            self.root.after(0, lambda: [self.source_file_sha256.set(f"Error"), self.update_status(f"Hash error: {e}")])
        finally:
            self.root.after(0, self.progress_bar.stop)

    def select_icon_file(self):
        filepath = filedialog.askopenfilename(title="Select Icon", filetypes=[("Images", "*.png;*.svg;*.jpg;*.jpeg"), ("All files", "*.*")])
        if filepath:
            self.icon_file_path.set(filepath)
            self.update_status(f"Icon selected")

    def select_executable_file(self):
        source_dir = self.source_path.get()
        if not os.path.isdir(source_dir):
            messagebox.showerror("Error", "Select a source directory first.")
            return
        filepath = filedialog.askopenfilename(title="Select Main Executable", initialdir=source_dir)
        if filepath and filepath.startswith(source_dir):
            rel_path = os.path.relpath(filepath, source_dir)
            self.fields["executable"].delete(0, tk.END)
            self.fields["executable"].insert(0, rel_path)
            self.fields["executable"].configure(style='TEntry')
        elif filepath:
            messagebox.showwarning("Invalid Selection", "Executable must be inside the source directory.")

    def autodetect_executable(self):
        source_dir = self.source_path.get()
        if not os.path.isdir(source_dir): return
        for f in ['main.py', '__main__.py', 'app.py']:
            for root, _, files in os.walk(source_dir):
                if f in files:
                    self.fields["executable"].delete(0, tk.END)
                    self.fields["executable"].insert(0, os.path.relpath(os.path.join(root, f), source_dir))
                    self.update_status(f"Auto-detected executable")
                    return
        self.update_status("No common executable found.")

    def calculate_sha256(self, filename):
        h = hashlib.sha256()
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()

    # ===================================================================================
    # REWRITTEN DEPENDENCY GENERATOR
    # ===================================================================================
    def run_dependency_generator(self):
        """
        Generates a single manifest module that installs all Python packages from
        requirements.txt. This method is compatible with older versions of
        flatpak-builder that do not support the 'pypi' source type.
        """
        source_dir = self.source_path.get()
        if not source_dir or not os.path.isdir(source_dir):
            messagebox.showwarning("Warning", "Please select a valid source directory first.")
            return

        req_path = Path(source_dir) / "requirements.txt"
        if not req_path.exists():
            if messagebox.askyesno("No requirements.txt", "No 'requirements.txt' file found. Scan project for imports to create one?"):
                self.update_status("Scanning for imports...")
                self._create_requirements_txt(source_dir)
            else:
                return

        if not req_path.exists() or req_path.stat().st_size == 0:
            messagebox.showinfo("No Dependencies", "The 'requirements.txt' is empty. No dependencies to generate.")
            return

        self.update_status("Generating dependencies...")
        self.progress_bar.start()

        def task():
            try:
                with open(req_path, 'r') as f:
                    # Read all non-empty, non-comment lines from the file
                    lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

                if not lines:
                    self.root.after(0, self._update_deps_result, "# requirements.txt is empty or only contains comments.\n")
                    return

                # Create a single pip install command for all packages
                install_command = f"pip3 install --prefix=/app {' '.join(lines)}"

                # Build the single manifest module
                module = [{
                    'name': "python-dependencies",
                    'buildsystem': 'simple',
                    'build-options': {
                        'build-args': ['--share=network']
                    },
                    'build-commands': [install_command],
                    'sources': [{
                        'type': 'script',
                        'commands': ["echo 'Installing Python dependencies...'"]
                    }]
                }]

                if yaml:
                    yaml_output = yaml.dump(module, sort_keys=False, indent=2)
                    self.root.after(0, self._update_deps_result, yaml_output)
                else:
                    self.root.after(0, self._update_deps_result, "# PyYAML not found.\n")

            except Exception as e:
                self.logger.error(f"Dependency generation failed: {e}", exc_info=True)
                self.root.after(0, lambda err=e: messagebox.showerror("Error", f"Failed to generate dependencies:\n{err}"))
            finally:
                self.root.after(0, self.progress_bar.stop)
                self.root.after(0, self.update_status, "Ready")
        threading.Thread(target=task, daemon=True).start()
    # ===================================================================================

    def _update_deps_result(self, yaml_output):
        self.fields["dependencies"].delete("1.0", tk.END)
        self.fields["dependencies"].insert("1.0", yaml_output)
        if yaml_output and not yaml_output.startswith('#'):
            self.update_status("Dependencies generated successfully.")
            messagebox.showinfo("Success", "Dependencies generated successfully!")
        else:
            self.update_status("Failed to generate dependencies.")
            messagebox.showwarning("Warning", "Could not generate dependencies for one or more packages.")

    def _create_requirements_txt(self, source_dir):
        imports = set()
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            tree = ast.parse(f.read(), filename=file_path)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                [imports.add(a.name.split('.')[0]) for a in node.names]
                            elif isinstance(node, ast.ImportFrom) and node.module:
                                imports.add(node.module.split('.')[0])
                    except Exception as e:
                        self.logger.warning(f"Could not parse AST for '{file_path}': {e}")
        req_path = os.path.join(source_dir, "requirements.txt")
        with open(req_path, "w") as f:
            standard_libs = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else set()
            filtered_imports = sorted([i for i in list(imports) if i not in standard_libs])
            f.write("\n".join(filtered_imports))
        self.logger.info(f"Created requirements.txt at {req_path} with {len(filtered_imports)} dependencies.")

    def validate_dependencies(self):
        deps_text = self.get_field_value("dependencies")
        if not deps_text:
            messagebox.showinfo("Validation", "No dependencies to validate.")
            return True
        if not yaml:
            messagebox.showwarning("Validation", "PyYAML library not found, cannot validate syntax.")
            return False
        try:
            yaml.safe_load(deps_text)
            messagebox.showinfo("Validation", "Dependencies syntax appears to be valid YAML.")
            return True
        except yaml.YAMLError as e:
            messagebox.showerror("Validation Error", f"The dependency syntax is invalid:\n\n{e}")
            return False

    def generate_files(self):
        if not self.validate_configuration(): return False
        save_dir = filedialog.askdirectory(title="Select Project Directory")
        if not save_dir: return False
        try:
            data = {k: self.get_field_value(k) for k in self.fields}
            app_id = data['appId']
            app_name = re.sub(r'[^a-zA-Z0-9_-]', '', data["appName"].replace(' ', '-')) or "app"
            main_module = self._generate_main_module(data, app_name)
            finish_args = self._generate_finish_args()
            yaml_content = self._generate_manifest_content(data, app_name, finish_args, main_module)
            self._write_manifest_file(save_dir, app_id, yaml_content)
            self._write_desktop_file(save_dir, f"{app_id}.desktop", data, app_name)
            self._copy_icon_file(save_dir)
            self._copy_source_archive(save_dir)
            self._write_build_script(save_dir, app_id)
            self._write_readme(save_dir, data)
            self.update_status("Files generated")
            self.unsaved_changes = False
            if messagebox.askyesno("Success", f"Files generated in:\n{save_dir}\n\nOpen directory?"):
                self.open_directory(save_dir)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate files: {e}")
            self.logger.error("File generation failed", exc_info=True)
            return False

    def _generate_main_module(self, data, app_name):
        module = {'name': app_name, 'buildsystem': data.get('buildSystem', 'simple'), 'sources': []}
        if data.get('buildSystem') == 'simple' and self.source_type.get() == 'directory':
            exec_call = f"python3 /app/share/{app_name}/{data['executable']}" if data['executable'].endswith('.py') else f"exec /app/share/{app_name}/{data['executable']}"
            module['build-commands'] = [f"install -d /app/share/{app_name}", f"cp -a ./* /app/share/{app_name}/", f"install -Dm755 /dev/stdin /app/bin/{app_name} <<'EOF'\n#!/bin/sh\n{exec_call} \"$@\"\nEOF"]
        if self.source_type.get() == 'archive':
            module['sources'].append({'type': 'archive', 'path': os.path.basename(self.source_path.get()), 'sha256': self.source_file_sha256.get()})
        else:
            module['sources'].append({ 'type': 'dir', 'path': self.source_path.get() })
        return module

    def _generate_finish_args(self):
        args = ['--share=ipc']
        perms = {"x11": "--socket=x11", "wayland": "--socket=wayland", "network": "--share=network", "home": "--filesystem=home", "dri": "--device=dri"}
        for k, arg in perms.items():
            if self.finish_args_vars.get(k, tk.BooleanVar()).get(): args.append(arg)
        if not any(s in ' '.join(args) for s in ['x11', 'wayland']): args.append('--socket=fallback-x11')
        custom = self.get_field_value('customPerms')
        if custom: args.extend([l.strip() for l in custom.split('\n') if l.strip()])
        return args

    def _generate_manifest_content(self, data, app_name, finish_args, main_module):
        manifest = {'app-id': data['appId'], 'runtime': data['runtime'], 'runtime-version': data['runtimeVersion'], 'sdk': data['sdk'], 'command': app_name, 'finish-args': finish_args, 'modules': []}
        if self.get_field_value('dependencies'):
            try:
                deps = yaml.safe_load(self.get_field_value('dependencies'))
                if isinstance(deps, list): manifest['modules'].extend(deps)
            except: pass
        manifest['modules'].append(main_module)
        return yaml.dump(manifest, sort_keys=False, indent=2) if yaml else "# PyYAML not installed"

    def _write_manifest_file(self, save_dir, app_id, content):
        self.last_yml_path = os.path.join(save_dir, f"{app_id}.yml")
        with open(self.last_yml_path, "w") as f: f.write(content)

    def _write_desktop_file(self, save_dir, filename, data, app_name):
        content = f"[Desktop Entry]\nName={data['appName']}\nComment={data['summary']}\nExec={app_name}\nIcon={data['appId']}\nType=Application\nCategories={data.get('category', 'Utility')};\n"
        with open(os.path.join(save_dir, filename), "w") as f: f.write(content)

    def _copy_icon_file(self, save_dir):
        if self.icon_file_path.get(): shutil.copy(self.icon_file_path.get(), save_dir)

    def _copy_source_archive(self, save_dir):
        if self.source_type.get() == 'archive' and self.source_path.get(): shutil.copy(self.source_path.get(), save_dir)

    def _write_build_script(self, save_dir, app_id):
        path = os.path.join(save_dir, "build.sh")
        content = (f"#!/bin/bash\nset -e\n\n# Build and install the application for the current user\n"
                   f"flatpak-builder --user --install --force-clean build-dir {app_id}.yml\n")
        with open(path, "w") as f: f.write(content)
        os.chmod(path, 0o755)

    def _write_readme(self, save_dir, data):
        content = f"# {data['appName']}\n\nBuild with `./build.sh` and run with `flatpak run {data['appId']}`."
        with open(os.path.join(save_dir, "README.md"), "w") as f: f.write(content)

    def open_directory(self, path):
        if sys.platform == "win32": os.startfile(path)
        elif sys.platform == "darwin": subprocess.run(["open", path])
        else: subprocess.run(["xdg-open", path])

    def new_project(self):
        if messagebox.askyesno("New Project", "Clear all settings?"):
            for w in self.fields.values():
                if isinstance(w, (tk.Text, scrolledtext.ScrolledText)): w.delete("1.0", tk.END)
                else:
                    w.delete(0, tk.END)
                    p = self.placeholders.get(w)
                    if p:
                        w.insert(0, p)
                        w.configure(style='Placeholder.TEntry')
            self.source_path.set("")
            self.icon_file_path.set("")
            self.source_type.set("directory")
            self.update_status("New project")

    def save_configuration(self):
        filepath = filedialog.asksaveasfilename(title="Save Config", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not filepath: return
        config = {
            'fields': {k: self.get_field_value(k) for k in self.fields},
            'vars': {'source_path': self.source_path.get(), 'icon_path': self.icon_file_path.get(), 'source_type': self.source_type.get()},
            'perms': {k: v.get() for k, v in self.finish_args_vars.items()}
        }
        with open(filepath, 'w') as f: json.dump(config, f, indent=4)
        self.update_status(f"Config saved")
        self.unsaved_changes = False

    def load_configuration(self):
        filepath = filedialog.askopenfilename(title="Load Config", filetypes=[("JSON", "*.json")])
        if not filepath: return
        with open(filepath, 'r') as f: config = json.load(f)
        for k, v in config.get('fields', {}).items():
            w = self.fields.get(k)
            if w:
                if isinstance(w, (tk.Text, scrolledtext.ScrolledText)):
                    w.delete("1.0", tk.END)
                    w.insert("1.0", v)
                else:
                    w.delete(0, tk.END)
                    w.insert(0, v)
                    w.configure(style='TEntry')
        variables = config.get('vars', {})
        self.source_path.set(variables.get('source_path', ''))
        self.icon_file_path.set(variables.get('icon_path', ''))
        self.source_type.set(variables.get('source_type', 'directory'))
        for k, v in config.get('perms', {}).items():
            if k in self.finish_args_vars: self.finish_args_vars[k].set(v)
        self.update_source_ui()
        self.update_status(f"Config loaded")

    def export_manifest_only(self):
        if not self.validate_configuration(): return
        data = {k: self.get_field_value(k) for k in self.fields}
        filepath = filedialog.asksaveasfilename(title="Export Manifest", defaultextension=".yml", filetypes=[("YAML", "*.yml")])
        if not filepath: return
        app_name = re.sub(r'[^a-zA-Z0-9_-]', '', data["appName"].replace(' ', '-')) or "app"
        main_module = self._generate_main_module(data, app_name)
        finish_args = self._generate_finish_args()
        content = self._generate_manifest_content(data, app_name, finish_args, main_module)
        with open(filepath, 'w') as f: f.write(content)
        messagebox.showinfo("Success", f"Manifest exported.")

    def refresh_runtime_list(self):
        self.update_status("Refreshing runtimes...")
        self.installed_runtimes, self.installed_sdks = self.detect_installed_refs()
        for key, getter in [("runtime", self.get_available_runtimes), ("sdk", self.get_available_sdks)]:
            combo = self.fields.get(key)
            if combo: combo['values'] = getter()
        self.on_runtime_selected()
        self.update_status("Runtimes refreshed")

    def show_about(self):
        messagebox.showinfo("About", "Flatpak Manifest Generator v2.5\n\nCreated by Grouvya.")

    def open_flatpak_docs(self):
        import webbrowser
        webbrowser.open("https://docs.flatpak.org/en/latest/")

    def open_donation_link(self):
        import webbrowser
        webbrowser.open("https://revolut.me/grouvya")

    def generate_app_id(self):
        author = self.get_field_value('author')
        app_name = self.get_field_value('appName')
        if not author or not app_name:
            messagebox.showwarning("Cannot Generate ID", "Please fill in the 'Author' and 'App Name' fields first.")
            return
        sane_author = re.sub(r'[^a-z0-9]+', '', author.lower().replace(' ', ''))
        sane_app_name = re.sub(r'[^a-z0-9]+', '', app_name.lower().replace(' ', ''))
        if not sane_author or not sane_app_name:
            messagebox.showwarning("Cannot Generate ID", "Author and App Name must contain valid alphanumeric characters.")
            return
        generated_id = f"io.github.{sane_author}.{sane_app_name}"
        app_id_entry = self.fields.get("appId")
        if app_id_entry:
            app_id_entry.delete(0, tk.END)
            app_id_entry.insert(0, generated_id)
            app_id_entry.configure(style='TEntry')
            self.validate_field("appId", required=True)
            self.update_status("App ID generated successfully.")

    def run_flatpak_app(self, with_terminal=False):
        app_id = self.get_field_value('appId')
        if not app_id:
            messagebox.showerror('Error', 'App ID is required.')
            return
        cmd = ['flatpak', 'run', app_id]
        if with_terminal:
            self._launch_terminal_command(' '.join(cmd))
        else:
            try:
                subprocess.Popen(cmd)
                self.update_status(f"Launched {app_id}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to launch: {e}")

    def _launch_terminal_command(self, command_str):
        term = next((t for t in ['gnome-terminal', 'konsole', 'xfce4-terminal', 'xterm'] if shutil.which(t)), None)
        if not term:
            messagebox.showerror("Error", "No supported terminal found.")
            return
        try:
            subprocess.Popen([term, '-e', f"bash -c '{command_str}; echo; read -p \"Press Enter to close...\"'"])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open terminal: {e}")

    def start_build_process(self):
        builder_cmd = self._find_executable("flatpak-builder")
        if not builder_cmd:
            messagebox.showerror("Error", "flatpak-builder not found in PATH or common locations.")
            return

        if not self.last_yml_path or not os.path.exists(self.last_yml_path):
            if not self.generate_files():
                self.update_status("Build canceled: manifest generation failed.")
                return

        sdk = self.get_field_value('sdk')
        sdk_version = self.get_field_value('sdkVersion')

        def proceed_with_build():
            build_dir = Path(self.last_yml_path).parent / 'build-dir'
            command = [builder_cmd, '--user', '--install', '--force-clean', str(build_dir), str(self.last_yml_path)]
            self.last_build_command = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in command)
            self.copy_command_button.config(state="normal")
            self._clear_output()
            self.notebook.select(self.output_frame)
            self._append_output(f"Starting build and install:\n{self.last_build_command}\n\n", 'CMD')
            self._run_command_in_thread(command, on_complete=self._on_build_and_install_complete)
        self._validate_sdk_installation(sdk, sdk_version, on_valid_callback=proceed_with_build)

    def _on_build_and_install_complete(self, return_code):
        if return_code == 0:
            self._append_output("\nBuild and install successful!\n", 'SUCCESS')
            messagebox.showinfo("Success", "Build and installation complete!")
        else:
            self._append_output("\nBuild and install failed.\n", 'ERROR')
            messagebox.showerror("Failed", "The build and install process failed. Check the Build Output tab for details.")

    def _run_command_in_thread(self, command, on_complete=None):
        def task():
            try:
                self._running_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                for line in iter(self._running_process.stdout.readline, ''):
                    self.output_queue.put(line)
                self._running_process.stdout.close()
                rc = self._running_process.wait()
                self.output_queue.put(None)
                if on_complete: self.root.after(0, on_complete, rc)
            except Exception as e:
                self.output_queue.put(f"\nFATAL ERROR: {e}\n")
                self.output_queue.put(None)
                if on_complete: self.root.after(0, on_complete, 1)
        self.progress_bar.start()
        thread = threading.Thread(target=task, daemon=True)
        thread.start()
        self.root.after(100, self._process_output_queue)

    def _process_output_queue(self):
        try:
            while True:
                line = self.output_queue.get_nowait()
                if line is None:
                    self.progress_bar.stop()
                    self._running_process = None
                    return
                self._append_output(line)
        except Exception:
            if self._running_process:
                self.root.after(100, self._process_output_queue)
            else:
                self.progress_bar.stop()

    def _clear_output(self):
        self.output_text.config(state='normal')
        self.output_text.delete('1.0', tk.END)
        self.output_text.config(state='disabled')

    def _append_output(self, text, tag=None):
        self.output_text.config(state='normal')
        self.output_text.insert(tk.END, text, tag)
        self.output_text.see(tk.END)
        self.output_text.config(state='disabled')
        self.root.update_idletasks()

    def detect_linux_distribution(self):
        try:
            with open('/etc/os-release') as f:
                info = {k.strip(): v.strip().strip('"') for k,v in (line.split('=',1) for line in f if '=' in line)}
            return info.get('ID', 'unknown'), info.get('VERSION_ID', 'unknown'), info.get('PRETTY_NAME', 'Unknown Linux')
        except:
            return 'unknown', 'unknown', 'Unknown Linux'

    def validate_configuration(self):
        self.logger.info('Validating configuration')
        errors, warnings = [], []
        required = {'appId': 'App ID','appName': 'App Name','summary': 'Summary','runtime': 'Runtime','runtimeVersion': 'Runtime Version','sdk': 'SDK','sdkVersion': 'SDK Version'}
        for field, label in required.items():
            if not self.get_field_value(field): errors.append(f"Missing required field: {label}")
        app_id = self.get_field_value('appId')
        if app_id:
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*){2,}$', app_id): errors.append("App ID must use reverse DNS notation (e.g., io.github.username.app)")
            elif not self.validate_dns_format(app_id): warnings.append("App ID format may not follow all common best practices (e.g., should be all lowercase).")
        if not self.source_path.get(): errors.append("Source location is required")
        if errors:
            messagebox.showerror("Validation Failed", "Please fix errors:\n\n" + "\n".join(f"• {e}" for e in errors))
            return False
        if warnings:
            return messagebox.askyesno("Validation Warnings", "Validation passed with warnings:\n\n" + "\n".join(f"• {w}" for w in warnings) + "\n\nContinue anyway?")
        messagebox.showinfo("Validation Passed", "Configuration is valid!")
        return True

    def validate_dns_format(self, app_id):
        parts = app_id.split('.')
        if len(parts) < 3: return False
        if not app_id.islower(): self.logger.warning("App ID is not all lowercase, which is a best practice.")
        return all(len(part) >= 1 for part in parts)

    def setup_autosave(self): pass
    def _load_recent_saves(self): return []
    def _load_sdk_cache(self): pass
    def _refresh_sdk_cache(self): pass
    def show_available_sdks(self): messagebox.showinfo("Info", "This feature is a work in progress.")
    def manage_sdks(self): messagebox.showinfo("Info", "This feature is a work in progress.")
    def show_sandbox_info(self): messagebox.showinfo("Info", "This feature is a work in progress.")
    def show_permissions_info(self): messagebox.showinfo("Info", "This feature is a work in progress.")
    def show_sandbox_filesystem(self): messagebox.showinfo("Info", "This feature is a work in progress.")
    def clean_app_data(self): messagebox.showinfo("Info", "This feature is a work in progress.")

    def handle_global_error(self, exc_type, exc_value, exc_traceback):
        self.logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        if self.root.winfo_exists():
            messagebox.showerror('Fatal Error', f'An unexpected error occurred:\n{exc_value}')
        self.cleanup_resources()
        self.root.destroy()

    def cleanup_resources(self):
        if self._running_process:
            try:
                self._running_process.terminate()
                self.logger.info("Terminated running process.")
            except Exception as e: self.logger.warning(f"Could not terminate process: {e}")
        for temp_file in list(self._temp_files):
            try:
                if os.path.exists(temp_file): os.unlink(temp_file)
            except Exception as e: self.logger.warning(f'Failed to remove temp file {temp_file}: {e}')
        self._temp_files.clear()

def main():
    if sys.version_info < (3, 6):
        print("Error: Python 3.6+ is required.", file=sys.stderr)
        sys.exit(1)

    missing_deps = []
    if not ThemedTk: missing_deps.append("ttkthemes")
    if not yaml: missing_deps.append("pyyaml")

    temp_root = None
    if missing_deps:
        temp_root = tk.Tk()
        temp_root.withdraw()
        if not messagebox.askyesno("Optional Dependencies", f"Missing: {', '.join(missing_deps)}. This may affect UI and functionality.\n\nContinue anyway?"):
            temp_root.destroy()
            sys.exit(0)
    if temp_root: temp_root.destroy()

    root = ThemedTk(theme="arc") if ThemedTk else tk.Tk()
    app = FlatpakBuilder(root)
    root.mainloop()

if __name__ == "__main__":
    main()
