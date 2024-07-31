import os
import random
import shutil
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QLabel, QTreeWidget, QTreeWidgetItem, QLineEdit,
    QWidget, QTableWidget, QTableWidgetItem, QCheckBox, QDialog, QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt


CONFIG_FILE = "files/config.json"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rocksmith DLC Manager")
        self.setGeometry(100, 100, 800, 600)

        # Initial state
        self.dlc_folder = None

        # Load previous config
        self.load_config()

        # Main layout
        layout = QVBoxLayout()

        # DLC folder selection
        self.dlc_folder_label = QLabel("No DLC folder selected")
        layout.addWidget(self.dlc_folder_label)
        select_dlc_button = QPushButton("Select DLC Folder")
        select_dlc_button.clicked.connect(self.select_dlc_folder)
        layout.addWidget(select_dlc_button)

        # DLC management buttons
        self.enable_all_button = QPushButton("Enable All DLC")
        self.enable_all_button.setEnabled(False)
        self.enable_all_button.clicked.connect(self.enable_all_dlc)
        layout.addWidget(self.enable_all_button)

        self.disable_all_button = QPushButton("Disable All DLC")
        self.disable_all_button.setEnabled(False)
        self.disable_all_button.clicked.connect(self.disable_all_dlc)
        layout.addWidget(self.disable_all_button)

        self.enable_random_button = QPushButton("Enable Random DLC")
        self.enable_random_button.setEnabled(False)
        self.enable_random_button.clicked.connect(self.enable_random_dlc)
        layout.addWidget(self.enable_random_button)

        self.reset_data_button = QPushButton("Reset All Data")
        self.reset_data_button.setEnabled(False)
        self.reset_data_button.clicked.connect(self.reset_all_data)
        layout.addWidget(self.reset_data_button)

        # DLC directory tree
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search directories...")
        self.search_bar.textChanged.connect(self.filter_tree)
        self.search_bar.setEnabled(False)
        layout.addWidget(self.search_bar)

        self.directory_tree = QTreeWidget()
        self.directory_tree.setHeaderLabel("DLC Directories")
        self.directory_tree.itemDoubleClicked.connect(self.edit_directory)
        self.directory_tree.setEnabled(False)
        layout.addWidget(self.directory_tree)

        # Check if we have a previously set DLC folder
        if self.dlc_folder:
            self.dlc_folder_label.setText(f"DLC Folder: {self.dlc_folder}")
            self.load_directory_tree()
            self.enable_all_button.setEnabled(True)
            self.disable_all_button.setEnabled(True)
            self.enable_random_button.setEnabled(True)
            self.reset_data_button.setEnabled(True)
            self.search_bar.setEnabled(True)
            self.directory_tree.setEnabled(True)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def select_dlc_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select DLC Folder")
        if folder:
            self.dlc_folder = folder
            self.dlc_folder_label.setText(f"DLC Folder: {self.dlc_folder}")
            self.save_config()
            self.load_directory_tree()
            self.enable_all_button.setEnabled(True)
            self.disable_all_button.setEnabled(True)
            self.enable_random_button.setEnabled(True)
            self.reset_data_button.setEnabled(True)
            self.search_bar.setEnabled(True)
            self.directory_tree.setEnabled(True)

    def load_directory_tree(self):
        self.directory_tree.clear()
        if self.dlc_folder:
            root_item = QTreeWidgetItem([os.path.basename(self.dlc_folder)])
            root_item.setData(0, Qt.UserRole, self.dlc_folder)
            self.directory_tree.addTopLevelItem(root_item)
            self.add_subdirectories(root_item, self.dlc_folder)

    def add_subdirectories(self, tree_item, path):
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                sub_item = QTreeWidgetItem([item])
                sub_item.setData(0, Qt.UserRole, item_path)
                tree_item.addChild(sub_item)
                self.add_subdirectories(sub_item, item_path)

    def filter_tree(self):
        search_text = self.search_bar.text().lower()
        for i in range(self.directory_tree.topLevelItemCount()):
            item = self.directory_tree.topLevelItem(i)
            self.filter_tree_item(item, search_text)

    def filter_tree_item(self, item, search_text):
        match = search_text in item.text(0).lower()
        item.setHidden(not match)
        for i in range(item.childCount()):
            child = item.child(i)
            child_match = self.filter_tree_item(child, search_text)
            match = match or child_match
        return match

    def enable_all_dlc(self):
        self.toggle_dlc_files(enable=True)

    def disable_all_dlc(self):
        self.toggle_dlc_files(enable=False)

    def enable_random_dlc(self):
        x, ok = QInputDialog.getInt(self, "Enable Random DLC", "Enter the number of DLCs to enable:")
        if ok:
            all_files = self.get_all_dlc_files()
            random_files = random.sample(all_files, min(x, len(all_files)))
            for file in random_files:
                self.toggle_file(file, enable=True)

    def toggle_dlc_files(self, enable):
        for root, dirs, files in os.walk(self.dlc_folder):
            for file in files:
                if file.endswith(".psarc") or file.endswith(".disabled"):
                    self.toggle_file(os.path.join(root, file), enable)

    def toggle_file(self, file, enable):
        if enable:
            new_file = file.replace(".disabled", ".psarc")
        else:
            new_file = file.replace(".psarc", ".disabled")
        os.rename(file, new_file)

    def reset_all_data(self):
        self.toggle_dlc_files(enable=True)
        self.dlc_folder = None
        self.dlc_folder_label.setText("No DLC folder selected")
        self.directory_tree.clear()
        self.enable_all_button.setEnabled(False)
        self.disable_all_button.setEnabled(False)
        self.enable_random_button.setEnabled(False)
        self.reset_data_button.setEnabled(False)
        self.search_bar.setEnabled(False)
        self.directory_tree.setEnabled(False)
        self.save_config()  # Clear the saved DLC folder

    def edit_directory(self, item, column):
        directory_path = item.data(0, Qt.UserRole)
        if directory_path:
            edit_all = QMessageBox.question(
                self, "Edit Directory",
                "Do you want to edit all subdirectories as well?",
                QMessageBox.Yes | QMessageBox.No
            )
            if edit_all == QMessageBox.Yes:
                directories = [directory_path]
                for root, dirs, files in os.walk(directory_path):
                    directories.extend([os.path.join(root, d) for d in dirs])
            else:
                directories = [directory_path]

            self.show_directory_editor(directories)

    def show_directory_editor(self, directories):
        editor_window = DirectoryEditorWindow(directories)
        editor_window.exec_()

    def get_all_dlc_files(self):
        dlc_files = []
        for root, dirs, files in os.walk(self.dlc_folder):
            for file in files:
                if file.endswith(".psarc") or file.endswith(".disabled"):
                    dlc_files.append(os.path.join(root, file))
        return dlc_files

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                self.dlc_folder = config.get("dlc_folder")

    def save_config(self):
        config = {"dlc_folder": self.dlc_folder}
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)


class DirectoryEditorWindow(QDialog):
    def __init__(self, directories):
        super().__init__()
        self.setWindowTitle("Edit Directory")
        self.setGeometry(100, 100, 800, 600)  # Changed window size to span entire length
        self.directories = directories

        layout = QVBoxLayout()

        # Table of DLC files
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["File Name", "Enabled"])
        self.table.horizontalHeader().setStretchLastSection(True)  # Make table span entire window width
        self.load_files()
        layout.addWidget(self.table)

        # Buttons for enabling/disabling all and random files
        button_layout = QHBoxLayout()

        enable_all_button = QPushButton("Enable All")
        enable_all_button.clicked.connect(self.enable_all)
        button_layout.addWidget(enable_all_button)

        disable_all_button = QPushButton("Disable All")
        disable_all_button.clicked.connect(self.disable_all)
        button_layout.addWidget(disable_all_button)

        enable_random_button = QPushButton("Enable Random")
        enable_random_button.clicked.connect(self.enable_random)
        button_layout.addWidget(enable_random_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_files(self):
        self.table.setRowCount(0)
        for directory in self.directories:
            for file in os.listdir(directory):
                if file.endswith(".psarc") or file.endswith(".disabled"):
                    self.add_file_row(directory, file)

    def add_file_row(self, directory, file):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)

        file_item = QTableWidgetItem(file)
        file_item.setFlags(Qt.ItemIsEnabled)
        self.table.setItem(row_position, 0, file_item)

        enable_checkbox = QCheckBox()
        enable_checkbox.setChecked(file.endswith(".psarc"))
        enable_checkbox.stateChanged.connect(
            lambda state, dir=directory, fname=file: self.toggle_file(dir, fname, state == Qt.Checked)
        )
        self.table.setCellWidget(row_position, 1, enable_checkbox)

    def toggle_file(self, directory, file, enable):
        old_file_path = os.path.join(directory, file)
        if enable:
            new_file_path = old_file_path.replace(".disabled", ".psarc")
            print(file + " has been enabled")
        else:
            new_file_path = old_file_path.replace(".psarc", ".disabled")
            print(file + " has been disabled")
        os.rename(old_file_path, new_file_path)
        self.load_files()

    def enable_all(self):
        for i in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(i, 1)
            checkbox.setChecked(True)

    def disable_all(self):
        for i in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(i, 1)
            checkbox.setChecked(False)

    def enable_random(self):
        x, ok = QInputDialog.getInt(self, "Enable Random Files", "Enter the number of files to enable:")
        if ok:
            checkboxes = [self.table.cellWidget(i, 1) for i in range(self.table.rowCount())]
            random_checkboxes = random.sample(checkboxes, min(x, len(checkboxes)))
            for checkbox in random_checkboxes:
                checkbox.setChecked(True)


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
