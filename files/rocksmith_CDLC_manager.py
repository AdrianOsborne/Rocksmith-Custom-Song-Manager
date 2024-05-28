import os
import shutil
import sys
import random
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
                             QFileDialog, QCheckBox, QHeaderView, QMessageBox, QLabel, QLineEdit, QInputDialog)
from PyQt5.QtCore import Qt, QMetaObject

class RocksmithDLCManager(QWidget):
    def __init__(self):
        super().__init__()
        self.ensure_disabled_folder()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Rocksmith DLC Manager')
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout()

        self.currentDirLabel = QLabel('No directory selected')
        layout.addWidget(self.currentDirLabel)

        self.selectDirButton = QPushButton('Select DLC Directory')
        self.selectDirButton.clicked.connect(self.select_directory)
        layout.addWidget(self.selectDirButton)

        self.disableAllButton = QPushButton('Disable All')
        self.disableAllButton.clicked.connect(self.disable_all_files)
        layout.addWidget(self.disableAllButton)

        self.enableAllButton = QPushButton('Enable All')
        self.enableAllButton.clicked.connect(self.enable_all_files)
        layout.addWidget(self.enableAllButton)

        self.enableRandomButton = QPushButton('Enable Random Songs')
        self.enableRandomButton.clicked.connect(self.enable_random_songs)
        layout.addWidget(self.enableRandomButton)

        filter_layout = QHBoxLayout()
        self.showEnabledCheckBox = QCheckBox('Show Enabled Files')
        self.showEnabledCheckBox.setChecked(True)
        self.showEnabledCheckBox.stateChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.showEnabledCheckBox)

        self.showDisabledCheckBox = QCheckBox('Show Disabled Files')
        self.showDisabledCheckBox.setChecked(True)
        self.showDisabledCheckBox.stateChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.showDisabledCheckBox)
        
        layout.addLayout(filter_layout)

        search_layout = QHBoxLayout()
        self.searchField = QLineEdit()
        self.searchField.setPlaceholderText('Search for a file...')
        self.searchField.textChanged.connect(self.apply_filters)
        search_layout.addWidget(self.searchField)

        self.enableSearchResultsButton = QPushButton('Enable Search Results')
        self.enableSearchResultsButton.clicked.connect(self.enable_search_results)
        self.enableSearchResultsButton.setEnabled(False)
        search_layout.addWidget(self.enableSearchResultsButton)

        self.disableSearchResultsButton = QPushButton('Disable Search Results')
        self.disableSearchResultsButton.clicked.connect(self.disable_search_results)
        self.disableSearchResultsButton.setEnabled(False)
        search_layout.addWidget(self.disableSearchResultsButton)
        
        layout.addLayout(search_layout)

        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(['File Name', 'Enabled'])
        self.tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tableWidget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tableWidget.setSelectionMode(QTableWidget.NoSelection)  # Disable selection
        layout.addWidget(self.tableWidget)

        self.setLayout(layout)
        self.load_saved_directory()

    def select_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select DLC Directory")
        if dir_path:
            with open('dlc_directory.txt', 'w') as f:
                f.write(dir_path)
            self.currentDirLabel.setText(f'Selected Directory: {dir_path}')
            self.load_directory(clear_table=True)

    def load_saved_directory(self):
        if os.path.exists('dlc_directory.txt'):
            with open('dlc_directory.txt', 'r') as f:
                self.dlc_dir = f.read().strip()
            self.currentDirLabel.setText(f'Selected Directory: {self.dlc_dir}')
            self.load_directory(clear_table=False)

    def load_directory(self, clear_table=False):
        if clear_table:
            self.tableWidget.setRowCount(0)

        if os.path.exists('dlc_directory.txt'):
            with open('dlc_directory.txt', 'r') as f:
                self.dlc_dir = f.read().strip()

            self.all_files = self.scan_directory(self.dlc_dir) + self.scan_directory(self.global_disabled_dir)
            self.all_files = sorted(self.all_files, key=lambda x: os.path.basename(x))

            self.populate_table(self.all_files)

            self.update_buttons_state()
            self.apply_filters()

    def scan_directory(self, directory):
        all_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                all_files.append(os.path.join(root, file))
        return all_files

    def populate_table(self, files):
        self.tableWidget.setRowCount(0)
        self.tableWidget.setUpdatesEnabled(False)  # Disable updates for batch processing
        
        for file_path in files:
            file_name = os.path.basename(file_path)
            enabled = os.path.dirname(file_path) == self.dlc_dir
            row_position = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row_position)
            
            self.tableWidget.setItem(row_position, 0, QTableWidgetItem(file_name))

            enabled_checkbox = QCheckBox()
            enabled_checkbox.setChecked(enabled)
            enabled_checkbox.stateChanged.connect(lambda state, path=file_path: self.toggle_file(path, state))

            self.tableWidget.setCellWidget(row_position, 1, enabled_checkbox)
            self.tableWidget.setRowHeight(row_position, 50)  # Adjust row height if necessary
        
        self.tableWidget.setUpdatesEnabled(True)  # Re-enable updates
        QMetaObject.invokeMethod(self.tableWidget, "repaint")  # Force repaint

    def toggle_file(self, file_path, state):
        file_name = os.path.basename(file_path)
        if state == Qt.Checked:
            source_path = os.path.join(self.global_disabled_dir, file_name)
            destination_path = os.path.join(self.dlc_dir, file_name)
        else:
            source_path = os.path.join(self.dlc_dir, file_name)
            destination_path = os.path.join(self.global_disabled_dir, file_name)

        if not os.path.exists(source_path):
            QMessageBox.critical(self, 'Error', f'File does not exist: {source_path}')
            return

        try:
            print(f"Moving file from {source_path} to {destination_path}")  # Debug statement
            shutil.move(source_path, destination_path)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to move file from {source_path} to {destination_path}: {e}')
        
        self.update_buttons_state()

    def search_file(self):
        self.apply_filters()

    def apply_filters(self):
        search_text = self.searchField.text().lower()
        show_enabled = self.showEnabledCheckBox.isChecked()
        show_disabled = self.showDisabledCheckBox.isChecked()

        for row in range(self.tableWidget.rowCount()):
            item = self.tableWidget.item(row, 0)
            checkbox = self.tableWidget.cellWidget(row, 1)
            if item and checkbox:
                matches_search = search_text in item.text().lower()
                is_enabled = checkbox.isChecked()

                show_row = matches_search and ((show_enabled and is_enabled) or (show_disabled and not is_enabled))
                self.tableWidget.setRowHidden(row, not show_row)

        has_search_text = bool(search_text)
        self.enableSearchResultsButton.setEnabled(has_search_text)
        self.disableSearchResultsButton.setEnabled(has_search_text)

    def ensure_disabled_folder(self):
        self.app_dir = os.path.dirname(__file__)
        self.global_disabled_dir = os.path.join(self.app_dir, 'disabled')
        if not os.path.exists(self.global_disabled_dir):
            os.makedirs(self.global_disabled_dir)

    def disable_all_files(self):
        self.tableWidget.setUpdatesEnabled(False)  # Disable updates for batch processing

        for row in range(self.tableWidget.rowCount()):
            checkbox = self.tableWidget.cellWidget(row, 1)
            if checkbox and checkbox.isChecked():
                file_name = self.tableWidget.item(row, 0).text()
                file_path = os.path.join(self.dlc_dir, file_name)
                destination_path = os.path.join(self.global_disabled_dir, file_name)
                if os.path.exists(file_path):
                    try:
                        checkbox.stateChanged.disconnect()
                        print(f"Disabling file: Moving from {file_path} to {destination_path}")  # Debug statement
                        shutil.move(file_path, destination_path)
                        checkbox.setChecked(False)
                        checkbox.stateChanged.connect(lambda state, path=file_path: self.toggle_file(path, state))
                    except Exception as e:
                        QMessageBox.critical(self, 'Error', f'Failed to move file from {file_path} to {destination_path}: {e}')

        self.tableWidget.setUpdatesEnabled(True)  # Re-enable updates
        QMetaObject.invokeMethod(self.tableWidget, "repaint")  # Force repaint
        self.update_buttons_state()

    def enable_all_files(self):
        self.tableWidget.setUpdatesEnabled(False)  # Disable updates for batch processing

        for row in range(self.tableWidget.rowCount()):
            checkbox = self.tableWidget.cellWidget(row, 1)
            if checkbox and not checkbox.isChecked():
                file_name = self.tableWidget.item(row, 0).text()
                file_path = os.path.join(self.global_disabled_dir, file_name)
                destination_path = os.path.join(self.dlc_dir, file_name)
                if os.path.exists(file_path):
                    try:
                        checkbox.stateChanged.disconnect()
                        print(f"Enabling file: Moving from {file_path} to {destination_path}")  # Debug statement
                        shutil.move(file_path, destination_path)
                        checkbox.setChecked(True)
                        checkbox.stateChanged.connect(lambda state, path=file_path: self.toggle_file(path, state))
                    except Exception as e:
                        QMessageBox.critical(self, 'Error', f'Failed to move file from {file_path} to {destination_path}: {e}')

        self.tableWidget.setUpdatesEnabled(True)  # Re-enable updates
        QMetaObject.invokeMethod(self.tableWidget, "repaint")  # Force repaint
        self.update_buttons_state()

    def enable_random_songs(self):
        num, ok = QInputDialog.getInt(self, "Enable Random Songs", "Enter the number of random songs to enable:", min=1)
        if not ok or num <= 0:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number greater than 0.")
            return

        disabled_files = [self.tableWidget.item(row, 0).text() for row in range(self.tableWidget.rowCount()) if not self.tableWidget.cellWidget(row, 1).isChecked()]
        if not disabled_files:
            QMessageBox.warning(self, "No Disabled Files", "There are no disabled files to enable.")
            return

        random.shuffle(disabled_files)
        num = min(num, len(disabled_files))

        self.disable_all_files()

        self.tableWidget.setUpdatesEnabled(False)  # Disable updates for batch processing

        for i in range(num):
            file_name = disabled_files[i]
            file_path = os.path.join(self.global_disabled_dir, file_name)
            destination_path = os.path.join(self.dlc_dir, file_name)
            if os.path.exists(file_path):
                try:
                    row = self.find_row_by_filename(file_name)
                    checkbox = self.tableWidget.cellWidget(row, 1)
                    checkbox.stateChanged.disconnect()
                    print(f"Enabling file: Moving from {file_path} to {destination_path}")  # Debug statement
                    shutil.move(file_path, destination_path)
                    checkbox.setChecked(True)
                    checkbox.stateChanged.connect(lambda state, path=file_path: self.toggle_file(path, state))
                except Exception as e:
                    QMessageBox.critical(self, 'Error', f'Failed to move file from {file_path} to {destination_path}: {e}')
        
        self.tableWidget.setUpdatesEnabled(True)  # Re-enable updates
        QMetaObject.invokeMethod(self.tableWidget, "repaint")  # Force repaint
        self.update_buttons_state()

    def enable_search_results(self):
        self.apply_bulk_operation_to_search_results(enable=True)

    def disable_search_results(self):
        self.apply_bulk_operation_to_search_results(enable=False)

    def apply_bulk_operation_to_search_results(self, enable):
        search_text = self.searchField.text().lower()
        operation = "Enabling" if enable else "Disabling"
        source_dir = self.global_disabled_dir if enable else self.dlc_dir
        dest_dir = self.dlc_dir if enable else self.global_disabled_dir

        self.tableWidget.setUpdatesEnabled(False)  # Disable updates for batch processing

        for row in range(self.tableWidget.rowCount()):
            item = self.tableWidget.item(row, 0)
            checkbox = self.tableWidget.cellWidget(row, 1)
            if item and checkbox:
                matches_search = search_text in item.text().lower()
                is_checked = checkbox.isChecked()
                should_update = matches_search and ((enable and not is_checked) or (not enable and is_checked))
                
                if should_update:
                    file_name = item.text()
                    source_path = os.path.join(source_dir, file_name)
                    destination_path = os.path.join(dest_dir, file_name)
                    if os.path.exists(source_path):
                        try:
                            checkbox.stateChanged.disconnect()
                            print(f"{operation} file: Moving from {source_path} to {destination_path}")  # Debug statement
                            if os.path.exists(destination_path):
                                os.remove(destination_path)
                            shutil.move(source_path, destination_path)
                            checkbox.setChecked(enable)
                            checkbox.stateChanged.connect(lambda state, path=file_name: self.toggle_file(path, state))
                        except Exception as e:
                            QMessageBox.critical(self, 'Error', f'Failed to move file from {source_path} to {destination_path}: {e}')

        self.tableWidget.setUpdatesEnabled(True)  # Re-enable updates
        QMetaObject.invokeMethod(self.tableWidget, "repaint")  # Force repaint
        self.update_buttons_state()

    def find_row_by_filename(self, filename):
        for row in range(self.tableWidget.rowCount()):
            if self.tableWidget.item(row, 0).text() == filename:
                return row
        return -1

    def update_buttons_state(self):
        all_in_dlc = all(self.tableWidget.cellWidget(row, 1).isChecked() for row in range(self.tableWidget.rowCount()))
        all_in_disabled = all(not self.tableWidget.cellWidget(row, 1).isChecked() for row in range(self.tableWidget.rowCount()))

        self.disableAllButton.setEnabled(not all_in_disabled)
        self.enableAllButton.setEnabled(not all_in_dlc)

        has_search_text = bool(self.searchField.text())
        self.enableSearchResultsButton.setEnabled(has_search_text)
        self.disableSearchResultsButton.setEnabled(has_search_text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = RocksmithDLCManager()
    ex.show()
    sys.exit(app.exec_())
