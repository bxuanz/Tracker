from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QCursor

class AnnotationCanvas(QWidget):
    # 信号: (rect, is_new_creation)
    # is_new_creation=True 表示新建框，False 表示修改旧框
    geometry_changed = pyqtSignal(QRectF, bool) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 500)
        self.setStyleSheet("background-color: #202020;")
        self.setMouseTracking(True) 
        
        self.pixmap = None
        self.view_scale = 1.0
        self.view_offset = QPointF(0, 0)
        self.annotations_to_draw = [] 
        
        # 交互状态
        self.mode = "IDLE" # 状态机: IDLE, DRAWING, PANNING, MOVING, RESIZING
        self.last_mouse_pos = QPointF()
        self.start_pos = QPointF()     
        self.current_rect = QRectF()   
        
        # 编辑状态变量
        self.active_rect_index = -1    
        self.active_rect_geo = QRectF() 
        
        # === 优化点: 加大鼠标判定范围 ===
        self.handle_size = 20  # 判定区域大小 (看不见但摸得着)

    def set_image(self, pixmap):
        self.pixmap = pixmap
        self.update()

    def set_annotations(self, annos):
        self.annotations_to_draw = annos
        self.active_rect_index = -1
        self.active_rect_geo = QRectF()
        
        # 寻找当前被选中的框，用于编辑
        for i, (rect, _, _, is_sel) in enumerate(annos):
            if is_sel:
                self.active_rect_index = i
                self.active_rect_geo = rect
                break
        self.update()

    def reset_view(self):
        if not self.pixmap: return
        cw, ch = self.width(), self.height()
        pw, ph = self.pixmap.width(), self.pixmap.height()
        self.view_scale = min(cw/pw, ch/ph) * 0.95
        new_w, new_h = pw * self.view_scale, ph * self.view_scale
        self.view_offset = QPointF((cw - new_w)/2, (ch - new_h)/2)
        self.update()

    def screen_to_buffer(self, pos):
        return (pos - self.view_offset) / self.view_scale

    def get_resize_handle(self, rect):
        # 获取右下角的控制点区域 (判定区)
        return QRectF(rect.right() - self.handle_size, rect.bottom() - self.handle_size, 
                      self.handle_size * 2, self.handle_size * 2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        if self.pixmap:
            painter.translate(self.view_offset)
            painter.scale(self.view_scale, self.view_scale)
            painter.drawPixmap(0, 0, self.pixmap)

            inv_scale = 1.0 / self.view_scale
            
            for i, (rect, color, label, is_sel) in enumerate(self.annotations_to_draw):
                # 如果是选中状态且正在拖拽，绘制实时的 active_rect_geo，否则绘制原始 rect
                draw_rect = self.active_rect_geo if (is_sel and self.mode in ["MOVING", "RESIZING"]) else rect
                
                pen_width = 2.0 * inv_scale if is_sel else 1.5 * inv_scale
                style = Qt.PenStyle.SolidLine if is_sel else Qt.PenStyle.DashLine
                painter.setPen(QPen(color, pen_width, style))
                
                brush = QColor(color); brush.setAlpha(40 if is_sel else 0)
                painter.setBrush(QBrush(brush))
                painter.drawRect(draw_rect)
                
                # === 优化点: 绘制高亮醒目的把手 ===
                if is_sel:
                    # 视觉大小 (比判定区稍小，显得精致)
                    vis_size = 12 * inv_scale
                    
                    # 白色边框 + 青色填充 (在深色背景下极高对比度)
                    painter.setPen(QPen(Qt.GlobalColor.white, 2 * inv_scale))
                    painter.setBrush(QBrush(Qt.GlobalColor.cyan))
                    
                    center = draw_rect.bottomRight()
                    painter.drawRect(QRectF(center - QPointF(vis_size, vis_size), 
                                            center + QPointF(vis_size, vis_size)))

                # 画标签
                painter.save()
                painter.translate(draw_rect.topLeft())
                painter.scale(inv_scale, inv_scale)
                font = painter.font(); font.setBold(True); painter.setFont(font)
                bg = QRectF(0, -22, max(60, len(label)*12), 20)
                painter.fillRect(bg, color)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(bg, Qt.AlignmentFlag.AlignCenter, label)
                painter.restore()

            if self.mode == "DRAWING":
                painter.setPen(QPen(Qt.GlobalColor.white, 1.0 * inv_scale, Qt.PenStyle.DotLine))
                painter.setBrush(QBrush(QColor(255, 255, 255, 30)))
                painter.drawRect(self.current_rect)

    def mousePressEvent(self, event):
        if not self.pixmap: return
        buf_pos = self.screen_to_buffer(event.position())
        
        if event.button() == Qt.MouseButton.RightButton:
            self.mode = "PANNING"
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            # 判定顺序：先看是否点把手(Resize) -> 再看是否点框内(Move) -> 否则是画图(Draw)
            if self.active_rect_index != -1:
                if self.get_resize_handle(self.active_rect_geo).contains(buf_pos):
                    self.mode = "RESIZING"; self.start_pos = buf_pos; return
                if self.active_rect_geo.contains(buf_pos):
                    self.mode = "MOVING"; self.start_pos = buf_pos; return

            self.mode = "DRAWING"
            self.start_pos = buf_pos
            self.current_rect = QRectF(buf_pos, buf_pos)

    def mouseMoveEvent(self, event):
        buf_pos = self.screen_to_buffer(event.position())
        
        # 鼠标样式逻辑
        if self.mode == "IDLE" and self.active_rect_index != -1:
            if self.get_resize_handle(self.active_rect_geo).contains(buf_pos):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif self.active_rect_geo.contains(buf_pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)

        if self.mode == "PANNING":
            delta = event.position() - self.last_mouse_pos
            self.view_offset += delta
            self.last_mouse_pos = event.position()
            self.update()
        elif self.mode == "DRAWING":
            self.current_rect = QRectF(self.start_pos, buf_pos).normalized()
            self.update()
        elif self.mode == "MOVING":
            delta = buf_pos - self.start_pos
            self.active_rect_geo.translate(delta)
            self.start_pos = buf_pos
            self.update()
        elif self.mode == "RESIZING":
            # 简单的右下角拉伸
            self.active_rect_geo = QRectF(self.active_rect_geo.topLeft(), buf_pos).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.mode = "IDLE"
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.mode == "DRAWING":
                img_rect = QRectF(0, 0, self.pixmap.width(), self.pixmap.height())
                final = self.current_rect.intersected(img_rect)
                if final.width() > 2 and final.height() > 2:
                    self.geometry_changed.emit(final, True) # True: 新建
            elif self.mode in ["MOVING", "RESIZING"]:
                self.geometry_changed.emit(self.active_rect_geo, False) # False: 修改
            
            self.mode = "IDLE"
            self.current_rect = QRectF()
            self.update()

    def wheelEvent(self, event):
        if not self.pixmap: return
        factor = 1.2 if event.angleDelta().y() > 0 else 1/1.2
        new_scale = self.view_scale * factor
        if 0.01 < new_scale < 50.0:
            mouse = event.position()
            img_pos = (mouse - self.view_offset) / self.view_scale
            self.view_offset = mouse - img_pos * new_scale
            self.view_scale = new_scale
            self.update()