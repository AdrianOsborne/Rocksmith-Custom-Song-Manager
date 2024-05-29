import os
import shutil
import sys
import random
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
                             QFileDialog, QCheckBox, QHeaderView, QMessageBox, QLabel, QLineEdit, QInputDialog, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QMetaObject

class InitialWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Select Root Directory')
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()

        self.searchField = QLineEdit()
        self.searchField.setPlaceholderText('Search for a directory...')
        self.searchField.textChanged.connect(self.search_directories)
        layout.addWidget(self.searchField)

        self.treeWidget = QTreeWidget()
        self.treeWidget.setHeaderLabels(["Directories"])
        layout.addWidget(self.treeWidget)

        button_layout = QHBoxLayout()

        self.chooseDirButton = QPushButton('Choose Directory')
        self.chooseDirButton.clicked.connect(self.choose_directory)
        button_layout.addWidget(self.chooseDirButton)

        self.openDirButton = QPushButton('Open Directory')
        self.openDirButton.clicked.connect(self.open_directory)
        button_layout.addWidget(self.openDirButton)

        layout.addLayout(button_layout)

        self.includeSubdirsCheckBox = QCheckBox('Include Files in Subdirectories')
        layout.addWidget(self.includeSubdirsCheckBox)

        self.moveAllToDisabledButton = QPushButton('Disable All Songs')
        self.moveAllToDisabledButton.clicked.connect(self.move_all_to_disabled)
        layout.addWidget(self.moveAllToDisabledButton)

        self.moveAllToEnabledButton = QPushButton('Enable All Songs')
        self.moveAllToEnabledButton.clicked.connect(self.move_all_to_enabled)
        layout.addWidget(self.moveAllToEnabledButton)

        self.setLayout(layout)

        self.load_saved_directory()

    def choose_directory(self):
        root_dir = QFileDialog.getExistingDirectory(self, "Select Root Directory")
        if root_dir:
            if os.path.exists('file_info.json'):
                reply = QMessageBox.question(self, 'Confirm', 'A directory is already selected. Do you want to overwrite it?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    return
            self.save_selected_directory(root_dir)
            self.load_directories(root_dir)

    def save_selected_directory(self, directory):
        with open('selected_root_directory.txt', 'w') as f:
            f.write(directory)
        self.scan_and_save_files(directory)

    def load_saved_directory(self):
        if os.path.exists('selected_root_directory.txt'):
            with open('selected_root_directory.txt', 'r') as f:
                selected_dir = f.read().strip()
            self.load_directories(selected_dir)

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
                self.hide()
                self.manager_window = RocksmithDLCManager(directory_path, self.includeSubdirsCheckBox.isChecked())
                self.manager_window.show()

    def scan_and_save_files(self, directory):
        file_info = {}
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory)
                file_info[file] = {
                    'path': relative_path,
                    'enabled': root == directory
                }

        with open('file_info.json', 'w') as f:
            json.dump(file_info, f, indent=4)

    def move_all_to_disabled(self):
        self.scan_and_save_files(self.treeWidget.topLevelItem(0).data(0, Qt.UserRole))
        file_info = self.load_file_info()
        for file, info in file_info.items():
            src_path = os.path.join(self.treeWidget.topLevelItem(0).data(0, Qt.UserRole), info['path'])
            dest_path = os.path.join(os.path.dirname(__file__), 'disabled', file)
            if not os.path.exists(os.path.dirname(dest_path)):
                os.makedirs(os.path.dirname(dest_path))
            shutil.move(src_path, dest_path)
            file_info[file]['enabled'] = False
        self.save_file_info(file_info)

    def move_all_to_enabled(self):
        file_info = self.load_file_info()
        for file, info in file_info.items():
            src_path = os.path.join(os.path.dirname(__file__), 'disabled', file)
            dest_path = os.path.join(self.treeWidget.topLevelItem(0).data(0, Qt.UserRole), info['path'])
            if not os.path.exists(os.path.dirname(dest_path)):
                os.makedirs(os.path.dirname(dest_path))
            shutil.move(src_path, dest_path)
            file_info[file]['enabled'] = True
        self.save_file_info(file_info)

    def load_file_info(self):
        with open('file_info.json', 'r') as f:
            return json.load(f)

    def save_file_info(self, file_info):
        with open('file_info.json', 'w') as f:
            json.dump(file_info, f, indent=4)

class RocksmithDLCManager(QWidget):
    def __init__(self, directory_path, include_subdirs):
        super().__init__()
        self.directory_path = directory_path
        self.include_subdirs = include_subdirs
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
        self.file_info = self.load_file_info()
        self.all_files = list(self.file_info.keys())
        self.all_files = sorted(self.all_files, key=lambda x: x)
        self.populate_table(self.all_files)
        self.update_buttons_state()
        self.apply_filters()

    def back_to_directory_selection(self):
        self.close()  
        initial_window.show()  

    def load_file_info(self):
        with open('file_info.json', 'r') as f:
            return json.load(f)

    def populate_table(self, files):
        self.tableWidget.setRowCount(0)
        self.tableWidget.setUpdatesEnabled(False)  

        for file in files:
            file_path = os.path.join(self.directory_path, self.file_info[file]['path'])
            enabled = self.file_info[file]['enabled']
            row_position = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row_position)

            self.tableWidget.setItem(row_position, 0, QTableWidgetItem(file))

            enabled_checkbox = QCheckBox()
            enabled_checkbox.setChecked(enabled)
            enabled_checkbox.stateChanged.connect(lambda state, f=file: self.toggle_file(f, state))

            self.tableWidget.setCellWidget(row_position, 1, enabled_checkbox)
            self.tableWidget.setRowHeight(row_position, 50)  

        self.tableWidget.setUpdatesEnabled(True)  
        QMetaObject.invokeMethod(self.tableWidget, "repaint")  

    def toggle_file(self, file, state):
        if state == Qt.Checked:
            src_path = os.path.join(os.path.dirname(__file__), 'disabled', file)
            dest_path = os.path.join(self.directory_path, self.file_info[file]['path'])
        else:
            src_path = os.path.join(self.directory_path, self.file_info[file]['path'])
            dest_path = os.path.join(os.path.dirname(__file__), 'disabled', file)

        if not os.path.exists(src_path):
            QMessageBox.critical(self, 'Error', f'File does not exist: {src_path}')
            return

        try:
            print(f"Moving file from {src_path} to {dest_path}")  
            shutil.move(src_path, dest_path)
            self.file_info[file]['enabled'] = (state == Qt.Checked)
            self.save_file_info()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to move file from {src_path} to {dest_path}: {e}')

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
        self.tableWidget.setUpdatesEnabled(False)  

        for row in range(self.tableWidget.rowCount()):
            checkbox = self.tableWidget.cellWidget(row, 1)
            if checkbox and checkbox.isChecked():
                file_name = self.tableWidget.item(row, 0).text()
                src_path = os.path.join(self.directory_path, self.file_info[file_name]['path'])
                dest_path = os.path.join(self.global_disabled_dir, file_name)
                if os.path.exists(src_path):
                    try:
                        checkbox.stateChanged.disconnect()
                        print(f"Disabling file: Moving from {src_path} to {dest_path}")  
                        shutil.move(src_path, dest_path)
                        self.file_info[file_name]['enabled'] = False
                        checkbox.setChecked(False)
                        checkbox.stateChanged.connect(lambda state, f=file_name: self.toggle_file(f, state))
                    except Exception as e:
                        QMessageBox.critical(self, 'Error', f'Failed to move file from {src_path} to {dest_path}: {e}')

        self.tableWidget.setUpdatesEnabled(True)  
        QMetaObject.invokeMethod(self.tableWidget, "repaint")  
        self.save_file_info()
        self.update_buttons_state()

    def enable_all_files(self):
        self.tableWidget.setUpdatesEnabled(False)  

        for row in range(self.tableWidget.rowCount()):
            checkbox = self.tableWidget.cellWidget(row, 1)
            if checkbox and not checkbox.isChecked():
                file_name = self.tableWidget.item(row, 0).text()
                src_path = os.path.join(self.global_disabled_dir, file_name)
                dest_path = os.path.join(self.directory_path, self.file_info[file_name]['path'])
                if os.path.exists(src_path):
                    try:
                        checkbox.stateChanged.disconnect()
                        print(f"Enabling file: Moving from {src_path} to {dest_path}")  
                        shutil.move(src_path, dest_path)
                        self.file_info[file_name]['enabled'] = True
                        checkbox.setChecked(True)
                        checkbox.stateChanged.connect(lambda state, f=file_name: self.toggle_file(f, state))
                    except Exception as e:
                        QMessageBox.critical(self, 'Error', f'Failed to move file from {src_path} to {dest_path}: {e}')

        self.tableWidget.setUpdatesEnabled(True)  
        QMetaObject.invokeMethod(self.tableWidget, "repaint")  
        self.save_file_info()
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
            src_path = os.path.join(self.global_disabled_dir, file_name)
            dest_path = os.path.join(self.directory_path, self.file_info[file_name]['path'])
            if os.path.exists(src_path):
                try:
                    row = self.find_row_by_filename(file_name)
                    checkbox = self.tableWidget.cellWidget(row, 1)
                    checkbox.stateChanged.disconnect()
                    print(f"Enabling file: Moving from {src_path} to {dest_path}")  
                    shutil.move(src_path, dest_path)
                    self.file_info[file_name]['enabled'] = True
                    checkbox.setChecked(True)
                    checkbox.stateChanged.connect(lambda state, f=file_name: self.toggle_file(f, state))
                except Exception as e:
                    QMessageBox.critical(self, 'Error', f'Failed to move file from {src_path} to {dest_path}: {e}')

        self.tableWidget.setUpdatesEnabled(True)  
        QMetaObject.invokeMethod(self.tableWidget, "repaint")  
        self.save_file_info()
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
                    src_path = os.path.join(source_dir, file_name)
                    dest_path = os.path.join(dest_dir, self.file_info[file_name]['path'])
                    if os.path.exists(src_path):
                        try:
                            checkbox.stateChanged.disconnect()
                            print(f"{operation} file: Moving from {src_path} to {dest_path}")  
                            if os.path.exists(dest_path):
                                os.remove(dest_path)
                            shutil.move(src_path, dest_path)
                            self.file_info[file_name]['enabled'] = enable
                            checkbox.setChecked(enable)
                            checkbox.stateChanged.connect(lambda state, f=file_name: self.toggle_file(f, state))
                        except Exception as e:
                            QMessageBox.critical(self, 'Error', f'Failed to move file from {src_path} to {dest_path}: {e}')

        self.tableWidget.setUpdatesEnabled(True)  
        QMetaObject.invokeMethod(self.tableWidget, "repaint")  
        self.save_file_info()
        self.update_buttons_state()

    def find_row_by_filename(self, filename):
        for row in range(self.tableWidget.rowCount()):
            if self.tableWidget.item(row, 0).text() == filename:
                return row
        return -1

    def update_buttons_state(self):
        all_in_dlc = all(self.tableWidget.cellWidget(row, 1).isChecked() for row in range(self.tableWidget.rowCount()))
        all_in_disabled = all(not self.tableWidget.cellWidget(row, 1).isChecked() for row in range(self.tableWidget.rowCount()))

        self.disableAllButton.setEnabled(all_in_disabled)
        self.enableAllButton.setEnabled(all_in_dlc)

        has_search_text = bool(self.searchField.text())
        self.enableSearchResultsButton.setEnabled(has_search_text)
        self.disableSearchResultsButton.setEnabled(has_search_text)

    def save_file_info(self):
        with open('file_info.json', 'w') as f:
            json.dump(self.file_info, f, indent=4)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    initial_window = InitialWindow()
    initial_window.show()
    sys.exit(app.exec_())