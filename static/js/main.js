/**
 * CAFE ANTIGRAVITY - MAIN JAVASCRIPT
 * Utilities, Toast Notifications, Modal Handlers, Formatting & API Helpers
 */

// Format Currency to Vietnamese Dong (VND)
function formatVND(amount) {
    if (amount === undefined || amount === null || isNaN(amount)) return '0 VND';
    return Number(amount).toLocaleString('vi-VN') + ' VND';
}

// Format Date Time
function formatDateTime(dateStr) {
    if (!dateStr) return '';
    try {
        const d = new Date(dateStr);
        return d.toLocaleString('vi-VN', {
            hour: '2-digit', minute: '2-digit',
            day: '2-digit', month: '2-digit', year: 'numeric'
        });
    } catch (e) {
        return dateStr;
    }
}

// Toast Notification System
function showToast(message, type = 'success', duration = 3500) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconClass = 'fa-check-circle';
    if (type === 'error') iconClass = 'fa-exclamation-circle';
    if (type === 'warning') iconClass = 'fa-triangle-exclamation';
    if (type === 'info') iconClass = 'fa-info-circle';

    toast.innerHTML = `
        <i class="fas ${iconClass} toast-icon"></i>
        <div class="toast-message">${message}</div>
    `;

    container.appendChild(toast);

    // Trigger animation
    setTimeout(() => {
        toast.classList.add('show');
    }, 50);

    // Auto dismiss
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentElement) {
                toast.parentElement.removeChild(toast);
            }
        }, 300);
    }, duration);
}

// Modal Helpers
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
}

// Confirmation Dialog Helper
function showConfirm(title, message, onConfirm) {
    let confirmModal = document.getElementById('global-confirm-modal');
    if (!confirmModal) {
        confirmModal = document.createElement('div');
        confirmModal.id = 'global-confirm-modal';
        confirmModal.className = 'modal-backdrop';
        confirmModal.innerHTML = `
            <div class="modal-box" style="max-width: 420px;">
                <div class="modal-header">
                    <h3 id="confirm-title" style="color: var(--primary-gold);"><i class="fas fa-question-circle"></i> Xác nhận</h3>
                    <button class="modal-close-btn" onclick="closeModal('global-confirm-modal')">&times;</button>
                </div>
                <div class="modal-body">
                    <p id="confirm-message" style="font-size: 14px; line-height: 1.5; color: var(--text-primary);"></p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary btn-sm" onclick="closeModal('global-confirm-modal')">Hủy bỏ</button>
                    <button id="confirm-action-btn" class="btn btn-danger btn-sm">Đồng ý</button>
                </div>
            </div>
        `;
        document.body.appendChild(confirmModal);
    }

    document.getElementById('confirm-title').innerHTML = `<i class="fas fa-question-circle"></i> ${title}`;
    document.getElementById('confirm-message').textContent = message;

    const actionBtn = document.getElementById('confirm-action-btn');
    actionBtn.onclick = function() {
        closeModal('global-confirm-modal');
        if (typeof onConfirm === 'function') onConfirm();
    };

    openModal('global-confirm-modal');
}

// Generic Fetch API Wrapper
async function apiCall(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    };
    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);
        const result = await response.json();
        return result;
    } catch (err) {
        console.error('API Error:', err);
        showToast('Lỗi kết nối máy chủ! Vui lòng thử lại.', 'error');
        throw err;
    }
}

// Live Clock Initializer
function initClock() {
    const clockEl = document.getElementById('live-clock');
    if (!clockEl) return;

    function update() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const dateStr = now.toLocaleDateString('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });
        clockEl.innerHTML = `<i class="far fa-clock"></i> <span>${timeStr} &bull; ${dateStr}</span>`;
    }
    update();
    setInterval(update, 1000);
}

// Print Bill Receipt Helper
function printBillReceipt(bill) {
    let billModal = document.getElementById('bill-print-modal');
    if (!billModal) {
        billModal = document.createElement('div');
        billModal.id = 'bill-print-modal';
        billModal.className = 'modal-backdrop';
        billModal.innerHTML = `
            <div class="modal-box" style="max-width: 380px; background: transparent; border: none;">
                <div class="printable-receipt" id="receipt-container"></div>
                <div style="display: flex; justify-content: center; gap: 10px; margin-top: 14px;">
                    <button class="btn btn-secondary btn-sm" onclick="closeModal('bill-print-modal')">Đóng</button>
                    <button class="btn btn-primary btn-sm" onclick="window.print()"><i class="fas fa-print"></i> In hóa đơn</button>
                </div>
            </div>
        `;
        document.body.appendChild(billModal);
    }

    const itemsHtml = bill.items.map(item => `
        <div class="receipt-item-line">
            <span>${item.item_name} x${item.quantity}</span>
            <span>${formatVND(item.subtotal)}</span>
        </div>
        ${item.notes ? `<div class="receipt-item-sub">Ghi chú: ${item.notes}</div>` : ''}
    `).join('');

    const container = document.getElementById('receipt-container');
    container.innerHTML = `
        <div class="receipt-paper">
            <h2>${bill.cafe_name}</h2>
            <div class="sub">${bill.cafe_address}</div>
            <div class="sub">Hotline: ${bill.cafe_phone}</div>
            <div class="sub">Wifi: ${bill.cafe_wifi}</div>
            <div class="receipt-divider"></div>
            
            <div class="receipt-row">
                <span>Số HĐ:</span>
                <span><strong>${bill.bill_number}</strong></span>
            </div>
            <div class="receipt-row">
                <span>Bàn / Vị trí:</span>
                <span><strong>${bill.table}</strong></span>
            </div>
            <div class="receipt-row">
                <span>Thu ngân:</span>
                <span>${bill.staff}</span>
            </div>
            <div class="receipt-row">
                <span>Thời gian:</span>
                <span>${bill.created_at}</span>
            </div>
            
            <div class="receipt-divider"></div>
            
            <div class="receipt-items">
                ${itemsHtml}
            </div>
            
            <div class="receipt-divider"></div>
            
            <div class="receipt-row">
                <span>Tạm tính:</span>
                <span>${formatVND(bill.subtotal)}</span>
            </div>
            ${bill.discount > 0 ? `
            <div class="receipt-row" style="color: #c0392b;">
                <span>Giảm giá (${bill.voucher_code || 'Voucher'}):</span>
                <span>-${formatVND(bill.discount)}</span>
            </div>
            ` : ''}
            
            <div class="receipt-row bold" style="font-size: 14px; margin-top: 6px;">
                <span>TỔNG CỘNG:</span>
                <span>${formatVND(bill.total)}</span>
            </div>
            <div class="receipt-row" style="font-size: 11px; color: #555;">
                <span>Hình thức:</span>
                <span>${bill.payment_method === 'cash' ? 'Tiền mặt' : (bill.payment_method === 'card' ? 'Quẹt thẻ' : 'Chuyển khoản')}</span>
            </div>
            
            <div class="receipt-divider"></div>
            <div class="receipt-footer">
                <p>Cảm ơn Quý khách & Hẹn gặp lại!</p>
                <p style="font-size: 9px; margin-top: 4px;">Powered by Antigravity POS</p>
            </div>
        </div>
    `;

    openModal('bill-print-modal');
}

// Collapsible Panel Helper
function togglePanel(panelId, headerEl) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    const icon = headerEl ? headerEl.querySelector('.panel-toggle-icon') : null;
    if (panel.style.display === 'none') {
        panel.style.display = '';
        if (icon) { icon.classList.remove('fa-chevron-down'); icon.classList.add('fa-chevron-up'); }
    } else {
        panel.style.display = 'none';
        if (icon) { icon.classList.remove('fa-chevron-up'); icon.classList.add('fa-chevron-down'); }
    }
}

// Global initialization
document.addEventListener('DOMContentLoaded', () => {
    initClock();

    // Close modal on backdrop click
    document.querySelectorAll('.modal-backdrop, .modal-overlay').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
                document.body.style.overflow = '';
            }
        });
    });
});
