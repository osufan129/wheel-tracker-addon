# Wheel Tracker Add-on for Home Assistant

This add-on provides a tool for tracking options trading using the "Wheel Strategy" which involves:

1. Selling Cash Secured Puts (CSPs)
2. If assigned, holding shares
3. Selling Covered Calls (CCs) on those shares
4. Potentially selling shares or having them called away

## Features

- Track Cash Secured Puts (CSPs)
- Manage Share Holdings
- Track Covered Calls (CCs)
- Plan CSP trades with built-in calculator
- View trading history and performance

## Configuration

The add-on has the following configuration options:

- **database_path**: Path to store the SQLite database (default: `/config/wheel-tracker/database.db`)
- **log_level**: Controls the verbosity of log output from the add-on

## Usage

After installing the add-on:

1. Start the add-on
2. Access the Wheel Tracker UI from the sidebar
3. Begin tracking your options trades!

## Support

If you encounter any issues with this add-on, please open an issue on GitHub. 