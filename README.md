# Flatpak Manifest Generator

A professional GUI application for creating Flatpak applications with ease. Built with Python and Tkinter, this tool simplifies the process of generating Flatpak manifests, managing dependencies, and building sandboxed Linux applications.

## Features

### Core Functionality
- **Intuitive Interface**: Modern GUI with tabbed organization and clear workflow
- **Manifest Generation**: Automatically generates properly formatted Flatpak manifest files
- **Dependency Management**: Auto-generates Python dependencies from requirements.txt
- **Multiple Source Types**: Support for both directory-based and archive-based sources
- **Build Integration**: Direct build and install functionality with real-time output
- **Configuration Management**: Save and load project configurations as JSON

### Advanced Features
- **Runtime Detection**: Automatically detects installed Flatpak runtimes and SDKs
- **SDK Management**: Install missing SDKs directly from the interface
- **Permission Configuration**: Visual controls for filesystem, device, and network permissions
- **Validation**: Comprehensive validation of all configuration fields
- **App ID Generator**: Smart generation of reverse-DNS app identifiers
- **Icon Support**: Easy icon file selection with format recommendations
- **Build System Support**: Multiple build systems (simple, meson, cmake-ninja, autotools, qmake)

## Requirements

### System Requirements
- Python 3.6 or higher
- Flatpak installed and configured
- flatpak-builder tool

### Python Dependencies
**Required:**
- tkinter (usually included with Python)

**Optional (recommended):**
- `ttkthemes` - For improved UI theming
- `pyyaml` - For dependency generation and manifest export

Install optional dependencies:
```bash
pip install ttkthemes pyyaml
```

## Installation

1. Clone or download this repository
2. Make the script executable:
```bash
chmod +x main.py
```
3. Run the application:
```bash
./main.py
```

## Usage

### Quick Start

1. **Basic Info Tab**
   - Enter your App ID (or use the Generate button)
   - Fill in app name, author, and summary
   - Optionally select an icon file

2. **Build Config Tab**
   - Select runtime and SDK (e.g., org.gnome.Platform)
   - Choose runtime and SDK versions
   - Select source type (directory or archive)
   - Browse to your source code location
   - Specify the main executable file

3. **Dependencies Tab**
   - Create or select a requirements.txt file in your source directory
   - Click "Auto-Generate Dependencies" to create dependency modules
   - Add any system dependencies if needed

4. **Permissions Tab**
   - Configure filesystem access, device permissions, and network access
   - Add custom finish-args if needed

5. **Generate and Build**
   - Click "Validate" to check your configuration
   - Click "Generate Files" to create all necessary files
   - Click "Build & Install" to build and install your Flatpak

### Generated Files

When you generate files, the tool creates:
- `[app-id].yml` - The Flatpak manifest
- `[app-id].desktop` - Desktop entry file
- `build.sh` - Build script for easy rebuilding
- `README.md` - Basic documentation
- Copies of your icon and source archive (if applicable)

### Menu Options

**File Menu:**
- New Project - Clear all fields and start fresh
- Save/Load Configuration - Persist your project settings
- Export Manifest Only - Generate just the manifest file

**Tools Menu:**
- Validate Configuration - Check for errors before building
- Test Application - Run the installed Flatpak
- SDK Management - View and manage installed SDKs

## Configuration

The application stores data in `~/.flatpak-generator/`:
- `saves/` - Saved project configurations
- `backups/` - Automatic backups
- `sdk_cache/` - Cached SDK information

## Dependency Generation

The dependency generator creates a single manifest module that installs all Python packages from your requirements.txt file. This approach is compatible with older versions of flatpak-builder that don't support the 'pypi' source type.

If no requirements.txt exists, the tool can scan your Python files and automatically create one based on detected imports.

## Building Applications

### Method 1: Using the GUI
Click "Build & Install" to build and install in one step. The tool will:
1. Validate your configuration
2. Check for required SDKs and offer to install them
3. Run flatpak-builder with appropriate flags
4. Display real-time build output

### Method 2: Using the Generated Script
Navigate to your project directory and run:
```bash
./build.sh
```

### Method 3: Manual Build
```bash
flatpak-builder --user --install --force-clean build-dir [app-id].yml
```

## Running Your Application

After building, run your Flatpak:
```bash
flatpak run [your-app-id]
```

Or use the "Test Application" menu option in the GUI.

## Troubleshooting

### SDK Not Found
If you receive an SDK error, the tool will offer to install it automatically from Flathub. Ensure you have:
- Internet connection
- Flathub remote configured
- Sufficient disk space

### Build Failures
Check the "Build Output" tab for detailed error messages. Common issues:
- Missing dependencies in requirements.txt
- Incorrect executable path
- Permission issues with source files

### Permission Denied
Ensure your source directory and files are readable, and that the main executable has appropriate permissions.

## Debug Mode

Enable debug mode for verbose logging:
```bash
FLATPAK_BUILDER_DEBUG=1 ./main.py
```

Logs are stored in `/tmp/flatpak-generator/`.

## Best Practices

1. **App IDs**: Use reverse-DNS notation (e.g., io.github.username.appname)
2. **Icons**: Use 128x128 PNG or SVG format
3. **Permissions**: Request only the permissions your app actually needs
4. **Testing**: Always test your Flatpak before distribution
5. **Dependencies**: Keep requirements.txt up to date

## Contributing

This is an open-source project. Contributions, bug reports, and feature requests are welcome.

## Support

If you find this tool helpful, consider supporting the creator at:
https://revolut.me/grouvya

## License

This project is provided as-is for the Flatpak community.

## Version

Current version: 2.5

---

**Created with ❤️ by Grouvya**
