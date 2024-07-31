import sys
import os
import json
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
                             QMessageBox, QInputDialog, QTreeWidgetItemIterator)
from PyQt5.QtCore import Qt

class Utils:
    def __init__(self):
        self.settings_file = "files/settings.json"
        self.dlc_data_file = "files/dlc_data.json"
        self.disabled_folder = "files/disabled/"
        if not os.path.exists(self.disabled_folder):
            os.makedirs(self.disabled_folder)
        self.dlc_data = self.load_dlc_data()

    def get_dlc_path(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as file:
                settings = json.load(file)
                return settings.get('dlc_path')
        return None

    def save_dlc_path(self, path):
        with open(self.settings_file, 'w') as file:
            json.dump({'dlc_path': path}, file)

    def load_dlc_data(self):
        if os.path.exists(self.dlc_data_file):
            with open(self.dlc_data_file, 'r') as file:
                return json.load(file)
        return {}

    def save_dlc_data(self):
        with open(self.dlc_data_file, 'w') as file:
            json.dump(self.dlc_data, file)

    def track_file(self, file_path):
        relative_path = os.path.relpath(file_path, self.get_dlc_path())
        if relative_path not in self.dlc_data:
            self.dlc_data[relative_path] = {"original_location": file_path, "enabled": True}
            self.save_dlc_data()

    def move_file(self, src, dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        os.rename(src, dest)

    def toggle_file(self, file_key, enable):
        file_info = self.dlc_data[file_key]
        src = file_info['original_location'] if not enable else os.path.join(self.disabled_folder, file_key)
        dest = os.path.join(self.disabled_folder, file_key) if not enable else file_info['original_location']
        self.move_file(src, dest)
        self.dlc_data[file_key]['enabled'] = enable
        self.save_dlc_data()

    def move_all_files(self, enable=True):
        for file_key, file_info in self.dlc_data.items():
            if file_info['enabled'] != enable:
                self.toggle_file(file_key, enable)

    def enable_random_files(self, num):
        disabled_files = [k for k, v in self.dlc_data.items() if not v['enabled']]
        random.shuffle(disabled_files)
        for file_key in disabled_files[:num]:
            self.toggle_file(file_key, enable=True)

    def reset_data(self):
        for file_key, file_info in self.dlc_data.items():
            if not file_info['enabled']:
                self.toggle_file(file_key, enable=True)
        if os.path.exists(self.settings_file):
            os.remove(self.settings_file)
        if os.path.exists(self.dlc_data_file):
            os.remove(self.dlc_data_file)

    def get_files_in_directory(self, directory, include_disabled=True):
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if filename.endswith('.psarc'):
                    relative_path = os.path.relpath(os.path.join(root, filename), self.get_dlc_path())
                    if include_disabled or self.dlc_data.get(relative_path, {}).get('enabled'):
                        files.append(relative_path)
        return files

    def get_enabled_files(self, directory):
        return [k for k, v in self.dlc_data.items() if v['enabled'] and k.startswith(os.path.relpath(directory, self.get_dlc_path()))]

    def get_disabled_files(self, directory):
        return [k for k, v in self.dlc_data.items() if not v['enabled'] and k.startswith(os.path.relpath(directory, self.get_dlc_path()))]

class DLCManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rocksmith DLC Manager")
        self.setGeometry(200, 200, 800, 600)
        self.utils = Utils()
        self.dlc_path = self.utils.get_dlc_path()

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self.filter_tree)
        self.layout.addWidget(self.search_bar)

        self.tree_widget = QTreeWidget(self)
        self.tree_widget.setHeaderLabel("DLC Directories")
        self.tree_widget.itemDoubleClicked.connect(self.edit_directory)
        self.layout.addWidget(self.tree_widget)

        self.enable_all_button = QPushButton("Enable All DLC", self)
        self.enable_all_button.clicked.connect(lambda: self.toggle_all_dlc(enable=True))
        self.layout.addWidget(self.enable_all_button)

        self.disable_all_button = QPushButton("Disable All DLC", self)
        self.disable_all_button.clicked.connect(lambda: self.toggle_all_dlc(enable=False))
        self.layout.addWidget(self.disable_all_button)

        self.random_enable_button = QPushButton("Enable Random DLC", self)
        self.random_enable_button.clicked.connect(self.enable_random_dlc)
        self.layout.addWidget(self.random_enable_button)

        self.reset_button = QPushButton("Reset All Data", self)
        self.reset_button.clicked.connect(self.reset_all_data)
        self.layout.addWidget(self.reset_button)

        if not self.dlc_path:
            self.select_dlc_folder()
        else:
            self.load_tree()

    def select_dlc_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select DLC Folder")
        if folder:
            self.dlc_path = folder
            self.utils.save_dlc_path(self.dlc_path)
            self.load_tree()

    def load_tree(self):
        self.tree_widget.clear()
        if not self.dlc_path:
            return
        root_item = QTreeWidgetItem([os.path.basename(self.dlc_path)])
        root_item.setData(0, Qt.UserRole, self.dlc_path)
        self.tree_widget.addTopLevelItem(root_item)
        self.populate_tree(root_item, self.dlc_path)
        self.tree_widget.expandAll()

    def populate_tree(self, parent_item, parent_path):
        for item in os.listdir(parent_path):
            item_path = os.path.join(parent_path, item)
            if os.path.isdir(item_path):
                tree_item = QTreeWidgetItem([item])
                tree_item.setData(0, Qt.UserRole, item_path)
                parent_item.addChild(tree_item)
                self.populate_tree(tree_item, item_path)

    def filter_tree(self):
        filter_text = self.search_bar.text().lower()
        iterator = QTreeWidgetItemIterator(self.tree_widget)
        while iterator.value():
            item = iterator.value()
            item.setHidden(filter_text not in item.text(0).lower())
            iterator += 1

    def toggle_all_dlc(self, enable):
        self.utils.move_all_files(enable=enable)
        self.load_tree()

    def enable_random_dlc(self):
        num, ok = QInputDialog.getInt(self, "Enable Random DLC", "Number of DLCs to enable:", 1, 1, len(self.utils.get_disabled_files(self.dlc_path)))
        if ok:
            self.utils.enable_random_files(num)
            self.load_tree()

    def reset_all_data(self):
        confirm = QMessageBox.question(self, "Confirm Reset", "Are you sure you want to reset all data? This will move all disabled files back to their original locations and clear all settings.")
        if confirm == QMessageBox.Yes:
            self.utils.reset_data()
            self.dlc_path = None
            self.select_dlc_folder()

    def edit_directory(self, item, column):
        dir_path = item.data(0, Qt.UserRole)
        self.directory_window = DirectoryWindow(self.dlc_path, dir_path, self.utils)
        self.directory_window.show()

class DirectoryWindow(QMainWindow):
    def __init__(self, dlc_path, dir_path, utils):
        super().__init__()
        self.dlc_path = dlc_path
        self.dir_path = dir_path
        self.utils = utils

        self.setWindowTitle(f"Edit Directory - {os.path.basename(self.dir_path)}")
        self.setGeometry(300, 300, 800, 600)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self.filter_table)
        self.layout.addWidget(self.search_bar)

        self.table_widget = QTableWidget(self)
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["File Name", "Enabled"])
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table_widget)

        self.enable_all_button = QPushButton("Enable All", self)
        self.enable_all_button.clicked.connect(lambda: self.toggle_all_files(enable=True))
        self.layout.addWidget(self.enable_all_button)

        self.disable_all_button = QPushButton("Disable All", self)
        self.disable_all_button.clicked.connect(lambda: self.toggle_all_files(enable=False))
        self.layout.addWidget(self.disable_all_button)

        self.random_enable_button = QPushButton("Enable Random", self)
        self.random_enable_button.clicked.connect(self.enable_random_files)
        self.layout.addWidget(self.random_enable_button)

        self.load_files()

    def load_files(self):
        all_files = self.utils.get_files_in_directory(self.dir_path, include_disabled=True)
        self.table_widget.setRowCount(len(all_files))
        for row, file_key in enumerate(all_files):
            file_name = os.path.basename(file_key)
            enabled = QTableWidgetItem(file_name)
            enabled.setFlags(enabled.flags() ^ Qt.ItemIsEditable)
            self.table_widget.setItem(row, 0, enabled)

            checkbox = QCheckBox(self)
            checkbox.setChecked(self.utils.dlc_data[file_key]['enabled'])
            checkbox.stateChanged.connect(lambda state, fk=file_key: self.toggle_file(fk, state == Qt.Checked))
            self.table_widget.setCellWidget(row, 1, checkbox)

    def filter_table(self):
        filter_text = self.search_bar.text().lower()
        for row in range(self.table_widget.rowCount()):
            file_name = self.table_widget.item(row, 0).text().lower()
            self.table_widget.setRowHidden(row, filter_text not in file_name)

    def toggle_all_files(self, enable):
        for row in range(self.table_widget.rowCount()):
            checkbox = self.table_widget.cellWidget(row, 1)
            checkbox.setChecked(enable)

    def enable_random_files(self):
        num, ok = QInputDialog.getInt(self, "Enable Random Files", "Number of files to enable:", 1, 1, self.table_widget.rowCount())
        if ok:
            all_rows = list(range(self.table_widget.rowCount()))
            random.shuffle(all_rows)
            for row in all_rows[:num]:
                checkbox = self.table_widget.cellWidget(row, 1)
                checkbox.setChecked(True)

    def toggle_file(self, file_key, enable):
        self.utils.toggle_file(file_key, enable)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DLCManager()
    window.show()
    sys.exit(app.exec_())
