# Flatpak Manifest Generator v2.5

A comprehensive GUI application for creating professional Flatpak applications with ease. This tool simplifies the process of generating Flatpak manifests, managing dependencies, and building applications for Linux distribution.

## Features

### Core Functionality
- **Interactive GUI**: Modern, user-friendly interface with tabbed navigation
- **Manifest Generation**: Automatically creates YAML manifests with proper structure
- **Dependency Management**: Auto-generates Python dependencies from requirements.txt
- **Build Integration**: Direct integration with flatpak-builder for seamless building
- **Project Management**: Save/load configurations for reusable project templates

### Advanced Features
- **Multi-source Support**: Handle both directory and archive sources with automatic SHA256 calculation
- **Permission Management**: Comprehensive sandbox permission configuration
- **Runtime Detection**: Automatically detects installed Flatpak runtimes and SDKs
- **Validation**: Built-in configuration validation with helpful error messages
- **Testing Tools**: Run and test applications directly from the interface

## Prerequisites

### Required Dependencies
- Python 3.6 or higher
- Flatpak and flatpak-builder installed on your system
- tkinter (usually included with Python)

### Optional Dependencies
- `ttkthemes`: Enhanced UI theming
- `pyyaml`: YAML parsing and generation (highly recommended)

Install optional dependencies:
```bash
pip install ttkthemes pyyaml
```

## Installation

1. **Download the application**:
   ```bash
   wget https://example.com/main.py
   # or clone from repository
   ```

2. **Make executable**:
   ```bash
   chmod +x main.py
   ```

3. **Run the application**:
   ```bash
   python3 main.py
   ```

## Quick Start Guide

### 1. Basic Application Information
- **App ID**: Use reverse DNS notation (e.g., `io.github.username.appname`)
- **App Name**: Display name for your application
- **Author**: Your name or organization
- **Summary**: Brief description of your application
- **Icon**: Optional application icon (PNG/SVG recommended)
- **Category**: Primary application category

### 2. Build Configuration
- **Runtime**: Choose target runtime (GNOME, KDE, or Freedesktop)
- **SDK**: Corresponding SDK for development
- **Source Type**: Directory (for local development) or Archive (for distribution)
- **Source Location**: Path to your application source code
- **Build System**: Select appropriate build system (simple, meson, cmake, etc.)

### 3. Dependencies
- **Python Dependencies**: Auto-generate from requirements.txt or manually specify
- **System Dependencies**: Additional SDK packages if needed

### 4. Permissions
Configure sandbox permissions:
- **Filesystem Access**: Home directory, host filesystem
- **Hardware**: GPU acceleration, USB devices, audio
- **Network**: Internet access
- **Display**: X11, Wayland support
- **Custom**: Additional finish-args

### 5. Build and Test
- **Validate**: Check configuration for errors
- **Generate Files**: Create all necessary files (manifest, desktop file, build script)
- **Build & Install**: Compile and install the application

## Usage Examples

### Python Application
1. Set App ID: `io.github.myusername.myapp`
2. Choose source directory containing your Python project
3. Auto-detect main executable (e.g., `main.py`)
4. Generate dependencies from `requirements.txt`
5. Configure permissions (typically network, display)
6. Build and install

### Native Application
1. Configure with appropriate SDK (e.g., GNOME SDK for GTK apps)
2. Choose archive source with pre-compiled binaries
3. Select meson/cmake build system if applicable
4. Configure required system dependencies
5. Set appropriate permissions for your app's needs

## File Structure

After generation, your project directory will contain:
```
project-directory/
├── io.github.username.app.yml    # Main manifest file
├── io.github.username.app.desktop # Desktop entry
├── icon.png                       # Application icon (if provided)
├── source-archive.tar.gz         # Source archive (if used)
├── build.sh                      # Build script
└── README.md                     # Project documentation
```

## Configuration Files

The application stores configuration in `~/.flatpak-generator/`:
- `saves/`: Saved project configurations
- `backups/`: Automatic backups
- `sdk_cache/`: Cached SDK information

## Advanced Usage

### Custom Build Commands
For complex build processes, you can manually edit the generated manifest to add custom build commands, environment variables, or additional modules.

### Multiple Modules
The dependency generator creates modular manifests that can be extended with additional modules for complex applications with multiple components.

### Testing and Debugging
Use the built-in testing tools to:
- Run applications in the sandbox
- Inspect sandbox filesystem
- View permission details
- Clean application data

## Troubleshooting

### Common Issues

**flatpak-builder not found**
- Ensure flatpak-builder is installed: `sudo apt install flatpak-builder`
- Check if it's in your PATH

**SDK not available**
- The application can auto-install missing SDKs from Flathub
- Ensure Flathub remote is configured: `flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo`

**Permission denied errors**
- Ensure proper file permissions on source directories
- Check that executable files have execute permissions

**Build failures**
- Review build output in the "Build Output" tab
- Verify all dependencies are correctly specified
- Check that source paths are correct

### Debug Mode
Enable debug mode for detailed logging:
```bash
FLATPAK_BUILDER_DEBUG=1 python3 main.py
```

## Contributing

This application was created to simplify Flatpak development. Contributions, bug reports, and feature requests are welcome.

### Development Setup
1. Clone the repository
2. Install development dependencies
3. Run with debug mode enabled
4. Test with various project types

## License

This project is open-source. Please refer to the license file for details.

## Support

- **Documentation**: Built-in help and tooltips
- **Flatpak Documentation**: Access via Help menu
- **Community**: Flatpak community forums and documentation

## Acknowledgments

Created with ❤️ by Grouvya! 

Special thanks to the Flatpak community for creating an excellent application distribution platform.

---

**Version**: 2.5  
**Python Requirements**: 3.6+  
**Platform**: Linux (with Flatpak support)
