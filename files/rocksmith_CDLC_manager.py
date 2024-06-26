import os
import shutil
import sys
import json
import random
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
                             QFileDialog, QCheckBox, QHeaderView, QMessageBox, QLabel, QLineEdit, QInputDialog, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QMetaObject

class InitialWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.file_mapping = {}
        self.load_file_mapping()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Select Root Directory')
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()

        self.searchField = QLineEdit()
        self.searchField.setPlaceholderText('Search for a directory...')
        self.searchField.setDisabled(True)
        self.searchField.textChanged.connect(self.search_directories)
        layout.addWidget(self.searchField)

        self.treeWidget = QTreeWidget()
        self.treeWidget.setHeaderLabels(["Directories"])
        self.treeWidget.setDisabled(True)
        layout.addWidget(self.treeWidget)

        button_layout = QHBoxLayout()

        self.chooseDirButton = QPushButton('Assign DLC folder')
        self.chooseDirButton.clicked.connect(self.choose_directory)
        button_layout.addWidget(self.chooseDirButton)

        self.openDirButton = QPushButton('Modify songs in directory')
        self.openDirButton.setDisabled(True)
        self.openDirButton.clicked.connect(self.open_directory)
        button_layout.addWidget(self.openDirButton)

        layout.addLayout(button_layout)

        self.enableAllButton = QPushButton('Enable All Files')
        self.enableAllButton.setDisabled(True)
        self.enableAllButton.clicked.connect(self.enable_all_files)
        layout.addWidget(self.enableAllButton)

        self.disableAllButton = QPushButton('Disable All Files')
        self.disableAllButton.setDisabled(True)
        self.disableAllButton.clicked.connect(self.disable_all_files)
        layout.addWidget(self.disableAllButton)

        self.setLayout(layout)

        self.load_saved_directory()

    def choose_directory(self):
        new_root_dir = QFileDialog.getExistingDirectory(self, "Select Root Directory")
        if new_root_dir:
            if self.confirm_directory_switch(new_root_dir):
                self.switch_directories(new_root_dir)

    def confirm_directory_switch(self, new_root_dir):
        current_dir = self.get_saved_directory()
        if current_dir:
            reply = QMessageBox.question(self, 'Confirm Directory Switch',
                                         f'Are you sure you want to switch from {current_dir} to {new_root_dir}?\n'
                                         'This will move all files from the disabled folder back to their original locations.',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            return reply == QMessageBox.Yes
        return True

    def switch_directories(self, new_root_dir):
        self.move_disabled_files_to_original_location()
        self.save_selected_directory(new_root_dir)
        self.load_directories(new_root_dir)
        self.enable_elements()

    def move_disabled_files_to_original_location(self):
        disabled_dir = os.path.join(os.path.dirname(__file__), 'disabled')
        if os.path.exists(disabled_dir):
            for root, _, files in os.walk(disabled_dir):
                for file in files:
                    source_path = os.path.join(root, file)
                    destination_path = os.path.join(self.file_mapping.get(file, ""), file)
                    if not os.path.exists(destination_path):
                        new_path, ok = QFileDialog.getSaveFileName(self, "Assign new path for file", file)
                        if ok and new_path:
                            destination_path = new_path
                        else:
                            destination_path = os.path.join(self.get_saved_directory(), file)
                    try:
                        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                        shutil.move(source_path, destination_path)
                    except Exception as e:
                        QMessageBox.critical(self, 'Error', f'Failed to move file from {source_path} to {destination_path}: {e}')

    def save_selected_directory(self, directory):
        with open('selected_root_directory.txt', 'w') as f:
            f.write(directory)

    def load_saved_directory(self):
        if os.path.exists('selected_root_directory.txt'):
            with open('selected_root_directory.txt', 'r') as f:
                selected_dir = f.read().strip()
            self.load_directories(selected_dir)
            self.enable_elements()

    def load_directories(self, root_dir):
        self.treeWidget.clear()
        root_item = QTreeWidgetItem(self.treeWidget, [root_dir])
        root_item.setData(0, Qt.UserRole, root_dir)
        self.populate_tree(root_item, root_dir)

    def populate_tree(self, parent, path):
        for item_name in os.listdir(path):
            item_path = os.path.join(path, item_name)
            if os.path.isdir(item_path):
                child_item = QTreeWidgetItem(parent, [item_name])
                child_item.setData(0, Qt.UserRole, item_path)
                self.populate_tree(child_item, item_path)

    def search_directories(self):
        search_text = self.searchField.text().lower()
        for item in self.treeWidget.findItems("*", Qt.MatchWildcard | Qt.MatchRecursive):
            if search_text in item.text(0).lower():
                item.setHidden(False)
                parent_item = item.parent()
                while parent_item:
                    parent_item.setExpanded(True)
                    parent_item = parent_item.parent()
            else:
                item.setHidden(True)

    def open_directory(self):
        selected_items = self.treeWidget.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            directory_path = selected_item.data(0, Qt.UserRole)
            if os.path.isdir(directory_path):
                include_subdirectories, ok = QInputDialog.getItem(
                    self, "Include Subdirectories", "Do you want to include files from subdirectories?",
                    ["Yes", "No"], 0, False)
                if ok:
                    self.hide()
                    self.manager_window = RocksmithDLCManager(directory_path, include_subdirectories == "Yes", self.file_mapping)
                    self.manager_window.show()

    def enable_elements(self):
        self.searchField.setDisabled(False)
        self.treeWidget.setDisabled(False)
        self.openDirButton.setDisabled(False)
        self.enableAllButton.setDisabled(False)
        self.disableAllButton.setDisabled(False)

    def enable_all_files(self):
        self.apply_bulk_operation_to_all_files(enable=True)

    def disable_all_files(self):
        self.apply_bulk_operation_to_all_files(enable=False)

    def apply_bulk_operation_to_all_files(self, enable):
        source_dir = os.path.join(os.path.dirname(__file__), 'disabled') if enable else self.get_saved_directory()
        dest_dir = self.get_saved_directory() if enable else os.path.join(os.path.dirname(__file__), 'disabled')

        for root, _, files in os.walk(source_dir):
            for file in files:
                source_path = os.path.join(root, file)
                destination_path = os.path.join(dest_dir, file)
                try:
                    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                    shutil.move(source_path, destination_path)
                    self.update_file_mapping(file, destination_path)
                except Exception as e:
                    QMessageBox.critical(self, 'Error', f'Failed to move file from {source_path} to {destination_path}: {e}')

    def update_file_mapping(self, file_name, new_path):
        original_dir = os.path.dirname(new_path)
        self.file_mapping[file_name] = original_dir
        self.save_file_mapping()

    def load_file_mapping(self):
        if os.path.exists('file_mapping.json'):
            with open('file_mapping.json', 'r') as f:
                self.file_mapping = json.load(f)

    def save_file_mapping(self):
        with open('file_mapping.json', 'w') as f:
            json.dump(self.file_mapping, f)

    def get_saved_directory(self):
        if os.path.exists('selected_root_directory.txt'):
            with open('selected_root_directory.txt', 'r') as f:
                return f.read().strip()
        return ''

class RocksmithDLCManager(QWidget):
    def __init__(self, directory_path, include_subdirectories, file_mapping):
        super().__init__()
        self.directory_path = directory_path
        self.include_subdirectories = include_subdirectories
        self.file_mapping = file_mapping
        self.ensure_disabled_folder()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Rocksmith DLC Manager')
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()

        self.currentDirLabel = QLabel(f'Selected Directory: {self.directory_path}')
        layout.addWidget(self.currentDirLabel)

        self.backButton = QPushButton('Back to Directory Selection')
        self.backButton.clicked.connect(self.back_to_directory_selection)
        layout.addWidget(self.backButton)

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
        self.tableWidget.setSelectionMode(QTableWidget.NoSelection)
        layout.addWidget(self.tableWidget)

        self.setLayout(layout)
        self.load_directory()

    def load_directory(self):
        self.all_files = self.scan_directory(self.directory_path, self.include_subdirectories)
        self.all_files += self.scan_directory(self.global_disabled_dir, self.include_subdirectories, self.directory_path)
        self.all_files = sorted(self.all_files, key=lambda x: os.path.basename(x))
        self.populate_table(self.all_files)
        self.update_buttons_state()
        self.apply_filters()

    def back_to_directory_selection(self):
        self.close()
        initial_window.show()

    def scan_directory(self, directory, include_subdirectories, match_dir=None):
        all_files = []
        if include_subdirectories:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith('.psarc') and (match_dir is None or self.file_mapping.get(file, "").startswith(match_dir)):
                        all_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path) and file.endswith('.psarc') and (match_dir is None or self.file_mapping.get(file, "").startswith(match_dir)):
                    all_files.append(file_path)
        return all_files

    def populate_table(self, files):
        self.tableWidget.setRowCount(0)
        self.tableWidget.setUpdatesEnabled(False)

        for file_path in files:
            file_name = os.path.basename(file_path)
            enabled = os.path.dirname(file_path) == self.directory_path or (file_name in self.file_mapping and self.file_mapping[file_name] == self.directory_path)
            row_position = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row_position)

            self.tableWidget.setItem(row_position, 0, QTableWidgetItem(file_name))

            enabled_checkbox = QCheckBox()
            enabled_checkbox.setChecked(enabled)
            enabled_checkbox.stateChanged.connect(lambda state, path=file_path: self.toggle_file(path, state))

            self.tableWidget.setCellWidget(row_position, 1, enabled_checkbox)
            self.tableWidget.setRowHeight(row_position, 50)

        self.tableWidget.setUpdatesEnabled(True)
        QMetaObject.invokeMethod(self.tableWidget, "repaint")

    def toggle_file(self, file_path, state):
        file_name = os.path.basename(file_path)
        if state == Qt.Checked:
            source_path = os.path.join(self.global_disabled_dir, file_name)
            destination_path = self.file_mapping[file_name] if file_name in self.file_mapping else os.path.join(self.directory_path, file_name)
        else:
            source_path = os.path.join(self.directory_path, file_name)
            destination_path = os.path.join(self.global_disabled_dir, file_name)

        if not os.path.exists(source_path):
            QMessageBox.critical(self, 'Error', f'File does not exist: {source_path}')
            return

        try:
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            shutil.move(source_path, destination_path)
            if state == Qt.Checked:
                self.file_mapping[file_name] = os.path.dirname(destination_path)
            else:
                self.file_mapping[file_name] = self.directory_path
            self.save_file_mapping()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to move file from {source_path} to {destination_path}: {e}')

        self.update_buttons_state()

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
        self.apply_bulk_operation_to_all_files(enable=False)

    def enable_all_files(self):
        self.apply_bulk_operation_to_all_files(enable=True)

    def apply_bulk_operation_to_all_files(self, enable):
        self.tableWidget.setUpdatesEnabled(False)

        source_dir = self.global_disabled_dir if enable else self.directory_path
        dest_dir = self.directory_path if enable else self.global_disabled_dir

        for row in range(self.tableWidget.rowCount()):
            checkbox = self.tableWidget.cellWidget(row, 1)
            file_name = self.tableWidget.item(row, 0).text()
            file_path = os.path.join(source_dir, file_name)
            destination_path = os.path.join(dest_dir, file_name)
            if os.path.exists(file_path):
                try:
                    checkbox.stateChanged.disconnect()
                    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                    shutil.move(file_path, destination_path)
                    checkbox.setChecked(enable)
                    checkbox.stateChanged.connect(lambda state, path=file_name: self.toggle_file(path, state))
                    self.update_file_mapping(file_name, destination_path)
                except Exception as e:
                    QMessageBox.critical(self, 'Error', f'Failed to move file from {file_path} to {destination_path}: {e}')

        self.tableWidget.setUpdatesEnabled(True)
        QMetaObject.invokeMethod(self.tableWidget, "repaint")
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

        self.tableWidget.setUpdatesEnabled(False)

        for i in range(num):
            file_name = disabled_files[i]
            file_path = os.path.join(self.global_disabled_dir, file_name)
            destination_path = self.file_mapping[file_name] if file_name in self.file_mapping else os.path.join(self.directory_path, file_name)
            if os.path.exists(file_path):
                try:
                    row = self.find_row_by_filename(file_name)
                    checkbox = self.tableWidget.cellWidget(row, 1)
                    checkbox.stateChanged.disconnect()
                    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                    shutil.move(file_path, destination_path)
                    checkbox.setChecked(True)
                    checkbox.stateChanged.connect(lambda state, path=file_name: self.toggle_file(path, state))
                except Exception as e:
                    QMessageBox.critical(self, 'Error', f'Failed to move file from {file_path} to {destination_path}: {e}')

        self.tableWidget.setUpdatesEnabled(True)
        QMetaObject.invokeMethod(self.tableWidget, "repaint")
        self.update_buttons_state()

    def enable_search_results(self):
        self.apply_bulk_operation_to_search_results(enable=True)

    def disable_search_results(self):
        self.apply_bulk_operation_to_search_results(enable=False)

    def apply_bulk_operation_to_search_results(self, enable):
        search_text = self.searchField.text().lower()
        operation = "Enabling" if enable else "Disabling"
        source_dir = self.global_disabled_dir if enable else self.directory_path
        dest_dir = self.directory_path if enable else self.global_disabled_dir

        self.tableWidget.setUpdatesEnabled(False)

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
                    destination_path = self.file_mapping[file_name] if file_name in self.file_mapping else os.path.join(dest_dir, file_name)
                    if os.path.exists(source_path):
                        try:
                            checkbox.stateChanged.disconnect()
                            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                            if os.path.exists(destination_path):
                                os.remove(destination_path)
                            shutil.move(source_path, destination_path)
                            checkbox.setChecked(enable)
                            checkbox.stateChanged.connect(lambda state, path=file_name: self.toggle_file(path, state))
                            self.update_file_mapping(file_name, destination_path)
                        except Exception as e:
                            QMessageBox.critical(self, 'Error', f'Failed to move file from {source_path} to {destination_path}: {e}')

        self.tableWidget.setUpdatesEnabled(True)
        QMetaObject.invokeMethod(self.tableWidget, "repaint")
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

    def update_file_mapping(self, file_name, new_path):
        original_dir = os.path.dirname(new_path)
        self.file_mapping[file_name] = original_dir
        self.save_file_mapping()

    def save_file_mapping(self):
        with open('file_mapping.json', 'w') as f:
            json.dump(self.file_mapping, f)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    initial_window = InitialWindow()
    initial_window.show()
    sys.exit(app.exec_())
