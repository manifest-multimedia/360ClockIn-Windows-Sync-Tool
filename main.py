import sys
import json
import os
print("Python path:", sys.executable)
print("Python version:", sys.version)

import time
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox, QSpinBox, QComboBox, QHBoxLayout, QProgressBar
import mysql.connector
import mariadb
from pyzk.zk import ZK
from datetime import datetime

class SyncApp(QWidget):
    def __init__(self):
        super().__init__()
        self.sync_thread = None
        self.is_syncing = False
        self.initUI()
        self.config = {
            'host': '',
            'user': '',
            'password': '',
            'database': '',
            'db_type': 'mysql',
           
        }
        self.interval = 300
        self.load_settings()  # Load saved settings on startup
        
        # Auto-start sync if we have valid settings
        if all(self.config.values()):
            self.start_sync()
            self.is_syncing = True
            self.sync_control_button.setText('Pause Sync')
            self.status_label.setText('Status: Running')

    def initUI(self):
        # Set window size constraints
        self.setMinimumSize(400, 600)  # Minimum Width: 400px, Height: 500px
        # self.setMaximumSize(600, 700)  # Maximum Width: 600px, Height: 700px
        
        layout = QVBoxLayout()

        self.db_type_label = QLabel('Database Type:')
        self.db_type_selector = QComboBox()
        self.db_type_selector.addItems(['MySQL', 'MariaDB'])
        layout.addWidget(self.db_type_label)
        layout.addWidget(self.db_type_selector)

        self.host_label = QLabel('Database Host:')
        self.host_input = QLineEdit()
        layout.addWidget(self.host_label)
        layout.addWidget(self.host_input)

        self.user_label = QLabel('Database User:')
        self.user_input = QLineEdit()
        layout.addWidget(self.user_label)
        layout.addWidget(self.user_input)

        self.password_label = QLabel('Database Password:')
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)

        self.database_label = QLabel('Database Name:')
        self.database_input = QLineEdit()
        layout.addWidget(self.database_label)
        layout.addWidget(self.database_input)

        self.interval_label = QLabel('Sync Interval (seconds):')
        self.interval_input = QSpinBox()
        self.interval_input.setMinimum(60)  # Minimum interval of 1 minute
        self.interval_input.setValue(300)   # Default interval of 5 minutes
        layout.addWidget(self.interval_label)
        layout.addWidget(self.interval_input)

        self.test_connection_button = QPushButton('Test Database Connection')
        self.test_connection_button.clicked.connect(self.test_database_connection)
        layout.addWidget(self.test_connection_button)

        self.status_label = QLabel('Status: Not running')
        layout.addWidget(self.status_label)

        self.progress_text = QLabel('')
        layout.addWidget(self.progress_text)

        # Add progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.hide()  # Hidden by default
        layout.addWidget(self.progress_bar)

        button_layout = QHBoxLayout()
        
        self.save_config_button = QPushButton('Save Configuration')
        self.save_config_button.clicked.connect(self.save_configuration)
        button_layout.addWidget(self.save_config_button)

        self.sync_control_button = QPushButton('Start Auto Sync')
        self.sync_control_button.clicked.connect(self.toggle_sync)
        button_layout.addWidget(self.sync_control_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.setWindowTitle('360ClockIn Synchronizer for Windows')
        self.show()

    def load_settings(self):
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
                    
                    # Update UI with saved values
                    self.host_input.setText(self.config['host'])
                    self.user_input.setText(self.config['user'])
                    self.password_input.setText(self.config['password'])
                    self.database_input.setText(self.config['database'])
                    
                    # Set the correct database type (case-insensitive)
                    saved_db_type = self.config['db_type'].lower()
                    for i in range(self.db_type_selector.count()):
                        if self.db_type_selector.itemText(i).lower() == saved_db_type:
                            self.db_type_selector.setCurrentIndex(i)
                            break
                        
                    self.interval_input.setValue(self.config.get('interval', 300))
                    
                    # Change button text since config exists
                    self.save_config_button.setText('Update Settings')
        except Exception as e:
            print(f"Error loading settings: {e}")

    def get_db_connection(self):
        db_config = {
            'host': self.config['host'],
            'user': self.config['user'],
            'password': self.config['password'],
            'database': self.config['database']
        }
        db_type = self.config['db_type']
        
        try:
            if db_type == 'mysql':
                return mysql.connector.connect(**db_config)
            else:  # mariadb
                return mariadb.connect(**db_config)
        except (mysql.connector.Error, mariadb.Error) as e:
            raise Exception(f"Database connection failed: {e}")

    def test_database_connection(self):
        self.config['host'] = self.host_input.text()
        self.config['user'] = self.user_input.text()
        self.config['password'] = self.password_input.text()
        self.config['database'] = self.database_input.text()
        self.config['db_type'] = self.db_type_selector.currentText().lower()

        if not all(self.config.values()):
            QMessageBox.warning(self, 'Error', 'Please fill in all fields.')
            return

        try:
            connection = self.get_db_connection()
            connection.close()
            QMessageBox.information(self, 'Success', 'Database connection successful!')
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def save_configuration(self):
        self.config['host'] = self.host_input.text()
        self.config['user'] = self.user_input.text()
        self.config['password'] = self.password_input.text()
        self.config['database'] = self.database_input.text()
        self.config['db_type'] = self.db_type_selector.currentText().lower()
        self.interval = self.interval_input.value()

        if not all(self.config.values()):
            QMessageBox.warning(self, 'Error', 'Please fill in all fields.')
            return

        try:
            connection = self.get_db_connection()
            connection.close()
            QMessageBox.information(self, 'Success', 'Configuration saved successfully!')
            
            # Save settings to file
            config_to_save = self.config.copy()
            config_to_save['interval'] = self.interval
            with open('config.json', 'w') as f:
                json.dump(config_to_save, f)
            
            self.save_config_button.setText('Update Settings')
            
            # After successful connection and save
            if not self.is_syncing:
                self.start_sync()
                self.is_syncing = True
                self.sync_control_button.setText('Pause Sync')
                self.status_label.setText('Status: Running')
                self.progress_bar.show()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f"Failed to save settings: {str(e)}")

    def start_sync(self):
        self.sync_thread = SyncThread(self.config, self.interval)
        self.sync_thread.progress_signal.connect(self.update_progress)
        self.sync_thread.start()

    def toggle_sync(self):
        if not self.is_syncing:
            self.start_sync()
            self.sync_control_button.setText('Pause Sync')
            self.status_label.setText('Status: Running')
            self.progress_bar.show()
        else:
            self.stop_sync()
            self.sync_control_button.setText('Resume Sync')
            self.status_label.setText('Status: Paused')
            self.progress_bar.hide()
        self.is_syncing = not self.is_syncing

    def stop_sync(self):
        if self.sync_thread:
            self.sync_thread.stop()
            # Add a reasonable timeout for the thread to stop
            if not self.sync_thread.wait(5000):  # 5 second timeout
                self.progress_text.setText("Warning: Sync thread taking longer to stop...")
            self.progress_text.setText("Sync stopped")

    def update_progress(self, message):
        self.progress_text.setText(message)
        # Show progress bar during active operations
        if "Starting" in message or "Processing" in message:
            self.progress_bar.show()
        elif "complete" in message.lower():
            self.progress_bar.hide()

class SyncThread(QtCore.QThread):
    progress_signal = QtCore.pyqtSignal(str)
    
    def __init__(self, config, interval):
        super().__init__()
        self.config = config
        self.interval = interval
        self._running = True
        self._next_sync = 0

    def get_db_connection(self):
        db_config = {
            'host': self.config['host'],
            'user': self.config['user'],
            'password': self.config['password'],
            'database': self.config['database']
        }
        db_type = self.config['db_type']
        
        try:
            if db_type == 'mysql':
                return mysql.connector.connect(**db_config)
            else:  # mariadb
                return mariadb.connect(**db_config)
        except (mysql.connector.Error, mariadb.Error) as e:
            raise Exception(f"Database connection failed: {e}")

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                self.progress_signal.emit("Starting sync cycle...")
                self.sync_attendance_logs()
                self._next_sync = datetime.now().timestamp() + self.interval
                next_sync_time = datetime.fromtimestamp(self._next_sync).strftime('%H:%M:%S')
                self.progress_signal.emit(f"Sync complete. Next sync at {next_sync_time}")
            except Exception as e:
                self.progress_signal.emit(f"Error: {str(e)}")
            
            # Instead of one long sleep, break it into small intervals
            while self._running and datetime.now().timestamp() < self._next_sync:
                time.sleep(1)  # Sleep for 1 second at a time
                if not self._running:
                    break

    def sync_attendance_logs(self):
        # Add a check for running status at the start
        if not self._running:
            return
            
        connection = self.get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            query = "SELECT * FROM devices"
            cursor.execute(query)
            devices = cursor.fetchall()

            timeout = 2
            total_devices = len(devices)
            for idx, device in enumerate(devices, 1):
                # Check running status before processing each device
                if not self._running:
                    break
                    
                self.progress_signal.emit(f"Processing device {idx}/{total_devices}: {device['ip']}")
                zk_host = device['ip']
                zk_port = int(device['port'])

                try:
                    zk = ZK(zk_host, port=zk_port, timeout=timeout)
                    zk_conn = zk.connect()
                    logs = zk_conn.get_attendance()
                    for log in logs:
                        # First, check if this record already exists
                        check_query = """
                        SELECT id FROM device_attendance_logs 
                        WHERE employee_id = %(employee_id)s 
                        AND timestamp = %(timestamp)s
                        """
                        
                        log_data = {
                            'device_id': device['id'],
                            'employee_id': log.user_id,
                            'timestamp': log.timestamp,
                            'uid': getattr(log, 'uid', None),
                            'state': getattr(log, 'punch', None),
                            'type': getattr(log, 'status', 'UNKNOWN'),
                            'created_at': datetime.now(),
                            'updated_at': datetime.now()
                        }

                        cursor.execute(check_query, {
                            'employee_id': log_data['employee_id'],
                            'timestamp': log_data['timestamp']
                        })
                        
                        existing_record = cursor.fetchone()
                        
                        if existing_record:
                            # Option 1: Skip the record
                            # print(f"Skipping existing record for employee {log_data['employee_id']} at {log_data['timestamp']}")
                            # continue

                          #  Option 2: Or update the record if needed
                            update_query = """
                            UPDATE device_attendance_logs 
                            SET state = %(state)s,
                                type = %(type)s,
                                updated_at = %(updated_at)s
                            WHERE employee_id = %(employee_id)s 
                            AND timestamp = %(timestamp)s
                            """
                            cursor.execute(update_query, log_data)
                            print(f"Updated record for employee {log_data['employee_id']} at {log_data['timestamp']}")
                        else:
                            # Insert new record
                            insert_query = """
                            INSERT INTO device_attendance_logs 
                            (device_id, employee_id, timestamp, uid, state, type, created_at, updated_at)
                            VALUES 
                            (%(device_id)s, %(employee_id)s, %(timestamp)s, %(uid)s, %(state)s, %(type)s, %(created_at)s, %(updated_at)s)
                            """
                            cursor.execute(insert_query, log_data)
                            print(f"Inserted new record for employee {log_data['employee_id']} at {log_data['timestamp']}")

                    zk_conn.disconnect()
                    print(f"Synced attendance logs for {zk_host}:{zk_port}")
                except Exception as e:
                    print(f"Update DB Error: {zk_host}:{zk_port} - {e}")

            # Use database connection to commit, not ZK connection
            connection.commit()
            cursor.close()
            connection.close()
        except Exception as e:
            print(f"Sync Error: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SyncApp()
    sys.exit(app.exec_())