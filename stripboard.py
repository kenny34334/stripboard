import sys
import json
import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QMessageBox, QFrame, QLabel, QComboBox, QInputDialog,
    QDialog, QTextEdit, QDialogButtonBox, QMenu
)
from PyQt6.QtCore import Qt, QSize, QPoint, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QMouseEvent, QAction

CONFIG_FILE = "stripboard_projects.json"

# 20% intensere / fellere pastelkleuren
PASTEL_PALETTE = ["#ffffff", "#fef08a", "#bbf7d0", "#bae6fd"]


class ColorPickerPopup(QFrame):
    """Photoshop-stijl kleurenpalet popupvenster met kleine vierkante vakjes"""
    def __init__(self, target_row, parent_app, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.target_row = target_row
        self.parent_app = parent_app
        
        self.setStyleSheet("""
            ColorPickerPopup {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        
        for hex_code in PASTEL_PALETTE:
            swatch = ColorSwatchButton(hex_code, self)
            swatch.clicked.connect(lambda h=hex_code: self.select_color(h))
            layout.addWidget(swatch)

    def select_color(self, hex_code):
        self.parent_app.set_item_color(self.target_row, hex_code)
        self.close()


class ColorSwatchButton(QWidget):
    """Klikbaar klein vierkant kleurvakje (Photoshop swatches stijl)"""
    clicked = pyqtSignal()

    def __init__(self, hex_color, parent=None):
        super().__init__(parent)
        self.hex_color = hex_color
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = QColor(self.hex_color)
        painter.setBrush(color)
        
        if self.hex_color == "#ffffff":
            painter.setPen(QColor("#cbd5e1"))
        else:
            painter.setPen(QColor("#94a3b8"))
            
        painter.drawRoundedRect(2, 2, 22, 22, 4, 4)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class DialogueDialog(QDialog):
    """Popup om dialoog-ideeën bij een plotpoint te typen"""
    def __init__(self, current_text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dialoog-ideeën")
        self.setMinimumSize(480, 360)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        label = QLabel("Typ hier je dialoog-ideeën / notities:")
        label.setStyleSheet("font-size: 14px; color: #334155;")
        layout.addWidget(label)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(current_text)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 10px;
                font-size: 15px;
                color: #0f172a;
            }
        """)
        layout.addWidget(self.text_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_text(self):
        return self.text_edit.toPlainText().strip()


class StripboardApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop Film Plot Stripboard")
        self.setMinimumSize(660, 780)
        
        self.projects = {}
        self.current_project = "Mijn Eerste Film"
        self.load_data()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(16)

        # Project Selector Bar
        project_bar_layout = QHBoxLayout()
        project_bar_layout.setSpacing(8)
        
        project_label = QLabel("Film Project:")
        project_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #334155; background: transparent;")
        project_bar_layout.addWidget(project_label)
        
        self.project_combo = QComboBox()
        self.project_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 15px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.project_combo.currentIndexChanged.connect(self.change_project)
        project_bar_layout.addWidget(self.project_combo, stretch=1)

        new_proj_btn = QPushButton("+ Nieuw")
        new_proj_btn.clicked.connect(self.create_new_project)
        new_proj_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #ffffff;
                font-weight: bold;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1e293b;
            }
        """)
        project_bar_layout.addWidget(new_proj_btn)

        rename_proj_btn = QPushButton("Hernoem")
        rename_proj_btn.clicked.connect(self.rename_current_project)
        rename_proj_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #334155;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                color: #0f172a;
            }
        """)
        project_bar_layout.addWidget(rename_proj_btn)

        del_proj_btn = QPushButton("Verwijder")
        del_proj_btn.clicked.connect(self.delete_current_project)
        del_proj_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #ef4444;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #fef2f2;
                border: 1px solid #fca5a5;
            }
        """)
        project_bar_layout.addWidget(del_proj_btn)
        
        layout.addLayout(project_bar_layout)

        # Title & Description
        title_layout = QVBoxLayout()
        title_layout.setSpacing(3)
        
        self.header_label = QLineEdit()
        self.header_label.setReadOnly(True)
        self.header_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #0f172a; border: none; background: transparent;")
        title_layout.addWidget(self.header_label)
        
        sub_label = QLineEdit("Sleep = verplaatsen  •  1× klik = selecteren  •  Dubbelklik = plotzin bewerken  •  Rechtermuisknop = menu (dialoog / kleur / verwijderen)  •  Delete-toets = verwijderen")
        sub_label.setReadOnly(True)
        sub_label.setStyleSheet("font-size: 13px; color: #64748b; border: none; background: transparent;")
        title_layout.addWidget(sub_label)
        
        layout.addLayout(title_layout)

        # Input Form Layout
        form_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter a one-sentence plot point...")
        self.input_field.returnPressed.connect(self.add_strip)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 12px 15px;
                font-size: 18px;
            }
            QLineEdit:focus {
                border: 1px solid #94a3b8;
            }
        """)
        form_layout.addWidget(self.input_field)

        add_btn = QPushButton("Add Strip")
        add_btn.clicked.connect(self.add_strip)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f172a;
                color: #ffffff;
                font-weight: bold;
                border-radius: 10px;
                padding: 12px 20px;
                font-size: 17px;
            }
            QPushButton:hover {
                background-color: #1e293b;
            }
        """)
        form_layout.addWidget(add_btn)
        layout.addLayout(form_layout)

        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setDragEnabled(True)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDropIndicatorShown(True)
        self.list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.open_context_menu)
        
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 6px;
            }
            QListWidget::item {
                border: none;
                padding: 0px;
                margin-bottom: 4px;
            }
        """)
        self.list_widget.model().rowsMoved.connect(self.update_order_from_ui)
        layout.addWidget(self.list_widget)

        # Footer Actions Layout
        footer_layout = QHBoxLayout()
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.delete_selected)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #ef4444;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 10px 18px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #fef2f2;
                border: 1px solid #fca5a5;
            }
        """)
        footer_layout.addWidget(delete_btn)
        
        footer_layout.addStretch()

        clear_btn = QPushButton("Reset Board")
        clear_btn.clicked.connect(self.clear_all)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #64748b;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 10px 18px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                color: #0f172a;
            }
        """)
        footer_layout.addWidget(clear_btn)
        layout.addLayout(footer_layout)

        self.setStyleSheet("background-color: #f1f5f9;")
        self.update_project_combo()
        self.refresh_ui()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
        else:
            super().keyPressEvent(event)

    def load_data(self):
        self.projects = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.projects = data
                    elif isinstance(data, list):
                        self.projects = {"Mijn Eerste Film": data}
            except Exception:
                self.projects = {}
        
        if not self.projects:
            self.projects = {
                "Mijn Eerste Film": [
                    {"type": "separator", "text": ""},
                    {"type": "separator", "text": ""},
                    {"type": "separator", "text": ""}
                ]
            }
        
        self.current_project = list(self.projects.keys())[0]

        for proj_name, items in self.projects.items():
            if items and isinstance(items[0], str):
                self.projects[proj_name] = [{"type": "strip", "text": t, "color": "#ffffff", "dialogue": ""} for t in items]
            else:
                for item in items:
                    if item.get("type") == "strip":
                        if "color" not in item:
                            item["color"] = "#ffffff"
                        if "dialogue" not in item:
                            item["dialogue"] = ""
            
            while sum(1 for item in self.projects[proj_name] if item.get("type") == "separator") < 3:
                self.projects[proj_name].append({"type": "separator", "text": ""})

    def save_data(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.projects, f, ensure_ascii=False, indent=2)
            
            # AUTOMATISCHE GITHUB SYNC
            self.sync_to_github()
            
        except Exception as e:
            print("Error saving:", e)

    def sync_to_github(self):
        """Pusht automatisch de laatste JSON naar GitHub"""
        try:
            repo_dir = os.path.dirname(os.path.abspath(__file__))
            if not repo_dir:
                repo_dir = "."
                
            subprocess.run(["git", "add", CONFIG_FILE], cwd=repo_dir, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Auto-sync vanuit Desktop Stripboard App"], cwd=repo_dir, capture_output=True)
            result = subprocess.run(["git", "push"], cwd=repo_dir, capture_output=True)
            
            if result.returncode == 0:
                print("Succesvol gesynchroniseerd met GitHub!")
            else:
                print("Git push niet gelukt (geen internet of handmatige pull nodig).")
        except Exception as e:
            print("Fout bij GitHub sync:", e)

    def update_project_combo(self):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for proj_name in self.projects.keys():
            self.project_combo.addItem(proj_name)
        index = self.project_combo.findText(self.current_project)
        if index >= 0:
            self.project_combo.setCurrentIndex(index)
        self.project_combo.blockSignals(False)

    def change_project(self, index):
        proj_name = self.project_combo.currentText()
        if proj_name and proj_name in self.projects:
            self.current_project = proj_name
            self.refresh_ui()

    def create_new_project(self):
        title, ok = QInputDialog.getText(self, "Nieuwe Film", "Voer de titel van de film in:")
        if ok and title.strip():
            proj_name = title.strip()
            if proj_name in self.projects:
                QMessageBox.warning(self, "Bestaat al", "Er bestaat al een project met deze naam.")
                return
            
            self.projects[proj_name] = [
                {"type": "separator", "text": ""},
                {"type": "separator", "text": ""},
                {"type": "separator", "text": ""}
            ]
            self.current_project = proj_name
            self.save_data()
            self.update_project_combo()
            self.refresh_ui()

    def rename_current_project(self):
        old_name = self.current_project
        title, ok = QInputDialog.getText(self, "Film Hernoemen", "Voer de nieuwe titel van de film in:", text=old_name)
        if ok and title.strip():
            new_name = title.strip()
            if new_name == old_name:
                return
            if new_name in self.projects:
                QMessageBox.warning(self, "Bestaat al", "Er bestaat al een project met deze naam.")
                return
            
            self.projects[new_name] = self.projects.pop(old_name)
            self.current_project = new_name
            self.save_data()
            self.update_project_combo()
            self.refresh_ui()

    def delete_current_project(self):
        if len(self.projects) <= 1:
            QMessageBox.warning(self, "Kan niet verwijderen", "Je moet ten minste één filmproject overhouden.")
            return
        
        reply = QMessageBox.question(
            self, "Film Verwijderen", f"Weet je zeker dat je '{self.current_project}' wilt verwijderen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self.projects[self.current_project]
            self.current_project = list(self.projects.keys())[0]
            self.save_data()
            self.update_project_combo()
            self.refresh_ui()

    def refresh_ui(self):
        self.header_label.setText(self.current_project)
        scrollbar = self.list_widget.verticalScrollBar()
        scroll_value = scrollbar.value()
        current_row = self.list_widget.currentRow()

        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        
        current_items = self.projects.get(self.current_project, [])
        separator_index = 0
        
        for item_data in current_items:
            item = QListWidgetItem()
            if item_data["type"] == "separator":
                item.setText("")
                item.setData(Qt.ItemDataRole.UserRole, "separator")
                item.setSizeHint(QSize(0, 18))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                sep_widget = QWidget()
                sep_widget.setStyleSheet("background: transparent;")
                sep_layout = QHBoxLayout(sep_widget)
                sep_layout.setContentsMargins(0, 2, 0, 2)
                
                bar = QFrame()
                bar.setFixedHeight(8)
                
                if separator_index == 0:
                    bar.setStyleSheet("background-color: #334155; border-radius: 4px;")
                else:
                    bar.setStyleSheet("background-color: #64748b; border-radius: 4px;")
                
                separator_index += 1
                sep_layout.addWidget(bar)
                
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, sep_widget)
            else:
                item.setText(item_data["text"])
                item.setData(Qt.ItemDataRole.UserRole, "strip")
                item.setSizeHint(QSize(0, 48))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                bg_color = item_data.get("color", "#ffffff")
                
                border_color = "#cbd5e1"
                if bg_color == "#fef08a": border_color = "#eab308"
                elif bg_color == "#bbf7d0": border_color = "#22c55e"
                elif bg_color == "#bae6fd": border_color = "#0ea5e9"

                strip_widget = QWidget()
                strip_widget.setStyleSheet(f"""
                    QWidget {{
                        background-color: {bg_color};
                        border: 1px solid {border_color};
                        border-radius: 6px;
                    }}
                """)
                
                strip_layout = QHBoxLayout(strip_widget)
                strip_layout.setContentsMargins(14, 6, 14, 6)
                
                text_label = QLabel(item_data["text"])
                text_label.setStyleSheet("color: #0f172a; font-size: 16px; font-weight: bold; border: none; background: transparent;")
                strip_layout.addWidget(text_label)
                
                strip_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, strip_widget)
                
        self.list_widget.blockSignals(False)
        scrollbar.setValue(scroll_value)
        if current_row >= 0 and current_row < self.list_widget.count():
            self.list_widget.setCurrentRow(current_row)

    def add_strip(self):
        text = self.input_field.text().strip()
        if not text:
            return
        
        if self.current_project not in self.projects:
            self.projects[self.current_project] = []
            
        self.projects[self.current_project].append({
            "type": "strip",
            "text": text,
            "color": "#ffffff",
            "dialogue": ""
        })
        self.save_data()
        self.refresh_ui()
        self.input_field.clear()
        self.input_field.setFocus()

    def delete_selected(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            current_items = self.projects[self.current_project]
            deleted_item = current_items.pop(row)
            if deleted_item["type"] == "separator":
                current_items.append({"type": "separator", "text": ""})
            self.save_data()
            self.refresh_ui()

    def clear_all(self):
        reply = QMessageBox.question(
            self, "Reset Board", f"Are you sure you want to reset all plot points for '{self.current_project}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.projects[self.current_project] = [
                {"type": "separator", "text": ""},
                {"type": "separator", "text": ""},
                {"type": "separator", "text": ""}
            ]
            self.save_data()
            self.refresh_ui()

    def update_order_from_ui(self):
        new_items = []
        current_items = self.projects[self.current_project]
        for i in range(self.list_widget.count()):
            ui_item = self.list_widget.item(i)
            item_type = ui_item.data(Qt.ItemDataRole.UserRole)
            if item_type == "separator":
                new_items.append({"type": "separator", "text": ""})
            else:
                old_color = "#ffffff"
                old_dialogue = ""
                if i < len(current_items) and current_items[i]["type"] == "strip":
                    old_color = current_items[i].get("color", "#ffffff")
                    old_dialogue = current_items[i].get("dialogue", "")
                new_items.append({
                    "type": "strip",
                    "text": ui_item.text(),
                    "color": old_color,
                    "dialogue": old_dialogue
                })
        self.projects[self.current_project] = new_items
        self.save_data()

    def open_context_menu(self, position: QPoint):
        item = self.list_widget.itemAt(position)
        if not item:
            return
        
        item_type = item.data(Qt.ItemDataRole.UserRole)
        if item_type != "strip":
            return
            
        row = self.list_widget.row(item)
        current_items = self.projects[self.current_project]
        if row < 0 or row >= len(current_items):
            return

        self.list_widget.setCurrentRow(row)

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 14px;
            }
            QMenu::item:selected {
                background-color: #f1f5f9;
            }
        """)

        action_dialogue = QAction("Dialoog-ideeën…", self)
        action_color = QAction("Kleur kiezen…", self)
        action_delete = QAction("Verwijderen", self)

        action_dialogue.triggered.connect(lambda: self.open_dialogue(row))
        action_color.triggered.connect(lambda: self.show_color_picker(row, position))
        action_delete.triggered.connect(self.delete_selected)

        menu.addAction(action_dialogue)
        menu.addAction(action_color)
        menu.addSeparator()
        menu.addAction(action_delete)

        menu.exec(self.list_widget.viewport().mapToGlobal(position))

    def show_color_picker(self, row, position):
        global_pos = self.list_widget.viewport().mapToGlobal(position)
        self.color_popup = ColorPickerPopup(row, self)
        self.color_popup.move(global_pos)
        self.color_popup.show()

    def open_dialogue(self, row: int):
        current_items = self.projects[self.current_project]
        if row < 0 or row >= len(current_items):
            return

        current_dialogue = current_items[row].get("dialogue", "")

        dialog = DialogueDialog(current_dialogue, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            current_items[row]["dialogue"] = dialog.get_text()
            self.save_data()

    def on_item_double_clicked(self, item: QListWidgetItem):
        if item.data(Qt.ItemDataRole.UserRole) != "strip":
            return

        row = self.list_widget.row(item)
        current_items = self.projects[self.current_project]

        if row < 0 or row >= len(current_items):
            return

        current_text = current_items[row].get("text", "")

        new_text, ok = QInputDialog.getText(
            self,
            "Plotzin bewerken",
            "Pas de plotzin aan:",
            text=current_text
        )

        if ok and new_text.strip():
            current_items[row]["text"] = new_text.strip()
            self.save_data()
            self.refresh_ui()

    def set_item_color(self, row, hex_code):
        current_items = self.projects[self.current_project]
        if 0 <= row < len(current_items) and current_items[row]["type"] == "strip":
            current_items[row]["color"] = hex_code
            self.save_data()
            self.refresh_ui()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StripboardApp()
    window.show()
    sys.exit(app.exec())