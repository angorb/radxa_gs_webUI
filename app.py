from flask import Flask, render_template, send_file, request, redirect, url_for, flash, jsonify
import os
from pathlib import Path
import configparser
from typing import Dict, List
import shutil
import subprocess
import yaml
import re
import subprocess
import platform

app = Flask(__name__)
app.secret_key = os.urandom(24)

MEDIA_FOLDER = '/media'
GS_KEY_PATH = '/etc/gs.key'
CONFIG_WHITELIST = [
    '/etc/wifibroadcast.cfg',
    '/config/scripts/screen-mode',
    '/config/scripts/osd',
    '/config/scripts/rec-fps'
]
COMMANDS_SCRIPT = os.path.join(os.path.dirname(__file__), 'commands.sh')

def ping_host(host, max_retries=3, timeout=10):
    """
    Returns True if host responds to a ping request, False otherwise.
    Includes retry logic and configurable timeout.
    
    Args:
        host (str): The host to ping
        max_retries (int): Maximum number of retry attempts
        timeout (int): Timeout in seconds for each ping attempt
    """
    # Option for count differs in Windows and Unix
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', host]
    
    for attempt in range(max_retries):
        try:
            subprocess.check_output(command, stderr=subprocess.STDOUT, timeout=timeout)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                time.sleep(2)  # Wait 2 seconds between retries
            continue
    
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/files')
def files():
    video_files = []
    if os.path.exists(MEDIA_FOLDER):
        for file in os.listdir(MEDIA_FOLDER):
            if file.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
                file_path = os.path.join(MEDIA_FOLDER, file)
                size = os.path.getsize(file_path)
                size_mb = round(size / (1024 * 1024), 2)
                video_files.append({
                    'name': file,
                    'size': size_mb
                })
    return render_template('files.html', files=video_files)

@app.route('/config')
def config():
    # List available config files
    available_configs = []
    for filepath in CONFIG_WHITELIST:
        if os.path.exists(filepath):
            available_configs.append({
                'path': filepath,
                'name': os.path.basename(filepath)
            })
            
    # Check if gs.key exists
    gs_key_exists = os.path.exists(GS_KEY_PATH)
    if gs_key_exists:
        gs_key_size = os.path.getsize(GS_KEY_PATH)
    else:
        gs_key_size = 0
        
    return render_template('config.html', 
                         configs=available_configs,
                         gs_key_exists=gs_key_exists,
                         gs_key_size=gs_key_size)

@app.route('/config/edit/<path:filepath>', methods=['GET', 'POST'])
def edit_config(filepath):
    # Normalize the filepath to handle URL encoding
    filepath = os.path.normpath('/' + filepath)
    
    # Validate filepath is in whitelist
    if filepath not in CONFIG_WHITELIST:
        print(f"Access denied. Filepath '{filepath}' not in whitelist: {CONFIG_WHITELIST}")
        return "Access denied", 403
    
    if request.method == 'POST':
        # Process form data
        new_config = {}
        for key in request.form:
            # Parse section and option from form field name
            if '__' in key:
                section, option = key.split('__')
                if section not in new_config:
                    new_config[section] = {}
                new_config[section][option] = request.form[key]
        
        # Write updated config
        if write_ini_file(filepath, new_config):
            flash('Configuration saved successfully!', 'success')
        else:
            flash('Error saving configuration', 'error')
        
        return redirect(url_for('edit_config', filepath=filepath))
    
    # Read current config
    config_data = read_ini_file(filepath)
    return render_template('edit_config.html', 
                         filepath=filepath,
                         filename=os.path.basename(filepath),
                         config=config_data)

@app.route('/config/gskey', methods=['POST'])
def upload_gskey():
    if 'gskey' not in request.files:
        flash('No file provided', 'error')
        return redirect(url_for('config'))
    
    file = request.files['gskey']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('config'))
    
    try:
        # Create a backup of the existing key if it exists
        if os.path.exists(GS_KEY_PATH):
            backup_path = GS_KEY_PATH + '.backup'
            shutil.copy2(GS_KEY_PATH, backup_path)
        
        # Save the new key file
        file.save(GS_KEY_PATH)
        # Set appropriate permissions
        os.chmod(GS_KEY_PATH, 0o644)
        
        flash('gs.key file updated successfully', 'success')
    except Exception as e:
        flash(f'Error updating gs.key: {str(e)}', 'error')
    
    return redirect(url_for('config'))

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(os.path.join(MEDIA_FOLDER, filename), as_attachment=True)
    except Exception as e:
        return f"Error downloading file: {str(e)}", 400

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    try:
        file_path = os.path.join(MEDIA_FOLDER, filename)
        os.remove(file_path)
        return redirect(url_for('files'))
    except Exception as e:
        return f"Error deleting file: {str(e)}", 400

@app.route('/camera')
def camera_settings():
    return render_template('camera_settings.html')

@app.route('/camera/load-config')
def load_camera_config():
    try:
        # First check if camera is reachable
        if not ping_host('10.5.0.10'):
            return jsonify({
                'success': False,
                'message': 'Camera is not reachable. Please check the connection.'
            }), 404
        
        # If ping successful, proceed with existing functionality
        wfb_output = subprocess.check_output(
            ['bash', '-c', f'source {COMMANDS_SCRIPT} && read_wfb_config'], 
            stderr=subprocess.STDOUT,
            text=True
        )
        
        majestic_output = subprocess.check_output(
            ['bash', '-c', f'source {COMMANDS_SCRIPT} && read_majestic_config'],
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Rest of your existing parsing logic...
        # Parse WFB config
        wfb_config = {}
        for line in wfb_output.splitlines():
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                wfb_config[key.strip()] = value.strip()
        
        # Parse Majestic YAML config
        try:
            yaml_content = majestic_output.replace("Reading majestic configuration", "").strip()
            majestic_config = yaml.safe_load(yaml_content)
            video_config = majestic_config.get('video0', {})
        except yaml.YAMLError as e:
            print(f"YAML parsing error: {e}")
            video_config = {}
        
        config = {
            'fps': str(video_config.get('fps', '60')),
            'size': str(video_config.get('size', '1920x1080')),
            'bitrate': str(video_config.get('bitrate', '4096')),
            'gopSize': str(video_config.get('gopSize', '1')),
            'channel': wfb_config.get('channel', '161'),
            'txpower_override': wfb_config.get('driver_txpower_override', '1'),
            'stbc': wfb_config.get('stbc', '0'),
            'ldpc': wfb_config.get('ldpc', '0'),
            'mcs_index': wfb_config.get('mcs_index', '1'),
            'fec_k': wfb_config.get('fec_k', '8'),
            'fec_n': wfb_config.get('fec_n', '12')
        }
        
        return jsonify({
            'success': True,
            'data': config
        })
        
    except subprocess.CalledProcessError as e:
        return jsonify({
            'success': False,
            'message': f'Error executing SSH commands: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }), 500

from flask import Flask, render_template, send_file, request, redirect, url_for, flash, jsonify
import os
from pathlib import Path
import configparser
from typing import Dict, List
import shutil
import subprocess
import yaml
import re
import subprocess
import platform

app = Flask(__name__)
app.secret_key = os.urandom(24)

MEDIA_FOLDER = '/media'
GS_KEY_PATH = '/etc/gs.key'
CONFIG_WHITELIST = [
    '/etc/wifibroadcast.cfg',
    '/config/scripts/screen-mode',
    '/config/scripts/osd',
    '/config/scripts/rec-fps'
]
COMMANDS_SCRIPT = os.path.join(os.path.dirname(__file__), 'commands.sh')

def ping_host(host):
    """
    Returns True if host responds to a ping request, False otherwise
    """
    # Option for count differs in Windows and Unix
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', host]
    
    try:
        subprocess.check_output(command, stderr=subprocess.STDOUT, timeout=5)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False

def read_ini_file(filepath: str) -> Dict:
    config = configparser.ConfigParser()
    try:
        config.read(filepath)
        return {section: dict(config[section]) for section in config.sections()}
    except Exception as e:
        return {}

def write_ini_file(filepath: str, data: Dict) -> bool:
    config = configparser.ConfigParser()
    try:
        # Load existing file first to preserve structure
        config.read(filepath)
        
        # Update with new values
        for section, values in data.items():
            if not config.has_section(section):
                config.add_section(section)
            for key, value in values.items():
                config.set(section, key, value)
        
        # Write to file
        with open(filepath, 'w') as f:
            config.write(f)
        return True
    except Exception as e:
        print(f"Error writing config: {str(e)}")
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/files')
def files():
    video_files = []
    if os.path.exists(MEDIA_FOLDER):
        for file in os.listdir(MEDIA_FOLDER):
            if file.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
                file_path = os.path.join(MEDIA_FOLDER, file)
                size = os.path.getsize(file_path)
                size_mb = round(size / (1024 * 1024), 2)
                video_files.append({
                    'name': file,
                    'size': size_mb
                })
    return render_template('files.html', files=video_files)

@app.route('/config')
def config():
    # List available config files
    available_configs = []
    for filepath in CONFIG_WHITELIST:
        if os.path.exists(filepath):
            available_configs.append({
                'path': filepath,
                'name': os.path.basename(filepath)
            })
            
    # Check if gs.key exists
    gs_key_exists = os.path.exists(GS_KEY_PATH)
    if gs_key_exists:
        gs_key_size = os.path.getsize(GS_KEY_PATH)
    else:
        gs_key_size = 0
        
    return render_template('config.html', 
                         configs=available_configs,
                         gs_key_exists=gs_key_exists,
                         gs_key_size=gs_key_size)

@app.route('/config/edit/<path:filepath>', methods=['GET', 'POST'])
def edit_config(filepath):
    # Normalize the filepath to handle URL encoding
    filepath = os.path.normpath('/' + filepath)
    
    # Validate filepath is in whitelist
    if filepath not in CONFIG_WHITELIST:
        print(f"Access denied. Filepath '{filepath}' not in whitelist: {CONFIG_WHITELIST}")
        return "Access denied", 403
    
    if request.method == 'POST':
        # Process form data
        new_config = {}
        for key in request.form:
            # Parse section and option from form field name
            if '__' in key:
                section, option = key.split('__')
                if section not in new_config:
                    new_config[section] = {}
                new_config[section][option] = request.form[key]
        
        # Write updated config
        if write_ini_file(filepath, new_config):
            flash('Configuration saved successfully!', 'success')
        else:
            flash('Error saving configuration', 'error')
        
        return redirect(url_for('edit_config', filepath=filepath))
    
    # Read current config
    config_data = read_ini_file(filepath)
    return render_template('edit_config.html', 
                         filepath=filepath,
                         filename=os.path.basename(filepath),
                         config=config_data)

@app.route('/config/gskey', methods=['POST'])
def upload_gskey():
    if 'gskey' not in request.files:
        flash('No file provided', 'error')
        return redirect(url_for('config'))
    
    file = request.files['gskey']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('config'))
    
    try:
        # Create a backup of the existing key if it exists
        if os.path.exists(GS_KEY_PATH):
            backup_path = GS_KEY_PATH + '.backup'
            shutil.copy2(GS_KEY_PATH, backup_path)
        
        # Save the new key file
        file.save(GS_KEY_PATH)
        # Set appropriate permissions
        os.chmod(GS_KEY_PATH, 0o644)
        
        flash('gs.key file updated successfully', 'success')
    except Exception as e:
        flash(f'Error updating gs.key: {str(e)}', 'error')
    
    return redirect(url_for('config'))

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(os.path.join(MEDIA_FOLDER, filename), as_attachment=True)
    except Exception as e:
        return f"Error downloading file: {str(e)}", 400

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    try:
        file_path = os.path.join(MEDIA_FOLDER, filename)
        os.remove(file_path)
        return redirect(url_for('files'))
    except Exception as e:
        return f"Error deleting file: {str(e)}", 400

@app.route('/camera')
def camera_settings():
    return render_template('camera_settings.html')

@app.route('/camera/load-config')
def load_camera_config():
    try:
        # First check if camera is reachable with retries
        if not ping_host('10.5.0.10', max_retries=3, timeout=10):
            return jsonify({
                'success': False,
                'message': 'Camera is not reachable after multiple attempts. Please check the connection.'
            }), 404
        
        # If ping successful, proceed with existing functionality
        wfb_output = subprocess.check_output(
            ['bash', '-c', f'source {COMMANDS_SCRIPT} && read_wfb_config'], 
            stderr=subprocess.STDOUT,
            text=True
        )
        
        majestic_output = subprocess.check_output(
            ['bash', '-c', f'source {COMMANDS_SCRIPT} && read_majestic_config'],
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Rest of your existing parsing logic...
        # Parse WFB config
        wfb_config = {}
        for line in wfb_output.splitlines():
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                wfb_config[key.strip()] = value.strip()
        
        # Parse Majestic YAML config
        try:
            yaml_content = majestic_output.replace("Reading majestic configuration", "").strip()
            majestic_config = yaml.safe_load(yaml_content)
            video_config = majestic_config.get('video0', {})
        except yaml.YAMLError as e:
            print(f"YAML parsing error: {e}")
            video_config = {}
        
        config = {
            'fps': str(video_config.get('fps', '60')),
            'size': str(video_config.get('size', '1920x1080')),
            'bitrate': str(video_config.get('bitrate', '4096')),
            'gopSize': str(video_config.get('gopSize', '1')),
            'channel': wfb_config.get('channel', '161'),
            'txpower_override': wfb_config.get('driver_txpower_override', '1'),
            'stbc': wfb_config.get('stbc', '0'),
            'ldpc': wfb_config.get('ldpc', '0'),
            'mcs_index': wfb_config.get('mcs_index', '1'),
            'fec_k': wfb_config.get('fec_k', '8'),
            'fec_n': wfb_config.get('fec_n', '12')
        }
        
        return jsonify({
            'success': True,
            'data': config
        })
        
    except subprocess.CalledProcessError as e:
        return jsonify({
            'success': False,
            'message': f'Error executing SSH commands: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }), 500

@app.route('/camera/update', methods=['POST'])
def update_camera_settings():
    try:
        changes = request.json
        if not changes:
            return jsonify({'success': False, 'message': 'No changes detected'}), 400
            
        # Map frontend field names to environment variables and function names
        field_mapping = {
            # Majestic config fields
            'fps': {'env': 'FPS', 'func': 'update_fps'},
            'size': {'env': 'SIZE', 'func': 'update_size'},
            'bitrate': {'env': 'BITRATE', 'func': 'update_bitrate'},
            'gopSize': {'env': 'GOPSIZE', 'func': 'update_gopSize'},
            # WFB config fields
            'channel': {'env': 'CHANNEL', 'func': 'update_channel'},
            'txpower_override': {'env': 'TXPOWER_OVERRIDE', 'func': 'update_txpower_override'},
            'stbc': {'env': 'STBC', 'func': 'update_stbc'},
            'ldpc': {'env': 'LDPC', 'func': 'update_ldpc'},
            'mcs_index': {'env': 'MCS_INDEX', 'func': 'update_mcs_index'},
            'fec_k': {'env': 'FEC_K', 'func': 'update_fec_k'},
            'fec_n': {'env': 'FEC_N', 'func': 'update_fec_n'}
        }
        
        # Only process fields that were actually changed
        changed_fields = set(changes.keys())
        if not changed_fields:
            return jsonify({'success': False, 'message': 'No valid changes detected'}), 400

        updated_fields = []
        for field, value in changes.items():
            if field in field_mapping:
                # Create a new environment with all current env vars
                env = os.environ.copy()
                # Set the specific environment variable for this field
                env[field_mapping[field]['env']] = str(value)
                
                print(f"Updating {field} to {value} using {field_mapping[field]['env']}")
                
                try:
                    # Run only the update function for this specific changed field
                    result = subprocess.run(
                        ['bash', '-c', f'source {COMMANDS_SCRIPT} && {field_mapping[field]["func"]}'],
                        env=env,
                        check=True,
                        text=True,
                        capture_output=True
                    )
                    print(f"Command output: {result.stdout}")
                    if result.stderr:
                        print(f"Command error: {result.stderr}")
                    updated_fields.append(field)
                except subprocess.CalledProcessError as e:
                    print(f"Error updating {field}: {str(e)}")
                    return jsonify({
                        'success': False, 
                        'message': f'Error updating {field}',
                        'updated_fields': updated_fields
                    }), 500
        
        return jsonify({
            'success': True,
            'message': f'Successfully updated: {", ".join(updated_fields)}'
        })
    except Exception as e:
        print(f"Error in update_camera_settings: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/camera/reboot', methods=['POST'])
def reboot_camera():
    try:
        # Check if camera is reachable
        if not ping_host('10.5.0.10'):
            return jsonify({
                'success': False,
                'message': 'Camera is not reachable. Please check the connection.'
            }), 404
            
        # Execute the reboot command
        result = subprocess.run(
            ['bash', '-c', f'source {COMMANDS_SCRIPT} && update_reboot'],
            check=True,
            text=True,
            capture_output=True
        )
        
        return jsonify({
            'success': True,
            'message': 'Camera reboot initiated successfully'
        })
        
    except subprocess.CalledProcessError as e:
        return jsonify({
            'success': False,
            'message': f'Error rebooting camera: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
