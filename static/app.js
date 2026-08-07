const STATUS_MAP = {
  '已发货': 'status-shipped',
  '处理中': 'status-processing',
  '已完成': 'status-complete',
  '待付款': 'status-pending'
};

const TIMELINE_STATUS_EVENT = {
  '待付款': '等待付款',
  '处理中': '仓库拣货',
  '已发货': '已发货',
  '已完成': '订单完成'
};

const input = document.getElementById('orderInput');
const searchBtn = document.getElementById('searchBtn');
const searchHint = document.getElementById('searchHint');
const orderDetail = document.getElementById('orderDetail');
const emptyState = document.getElementById('emptyState');
const handlerSelect = document.getElementById('handlerSelect');
const remindBtn = document.getElementById('remindBtn');
const reminderResult = document.getElementById('reminderResult');

let currentOrder = null;

function fmtCurrency(n) {
  return '\u00a5' + Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function statusClass(s) {
  return STATUS_MAP[s] || 'status-default';
}

function timelineActiveIndex(order) {
  const events = order.timeline || [];
  const targetEvent = TIMELINE_STATUS_EVENT[order.status];
  if (targetEvent) {
    const index = events.findIndex(function(t) { return t.event === targetEvent; });
    if (index !== -1) return index;
  }
  return events.length - 1;
}

function showHint(msg) {
  searchHint.textContent = msg;
  searchHint.classList.add('show');
}

function clearHint() {
  searchHint.textContent = '';
  searchHint.classList.remove('show');
}

function populateHandlers(handlers) {
  handlerSelect.innerHTML = '';
  handlers.forEach(function(handler) {
    const option = document.createElement('option');
    option.value = handler;
    option.textContent = handler;
    handlerSelect.appendChild(option);
  });
  remindBtn.disabled = handlers.length === 0;
}

function showReminderResult(text, isError) {
  reminderResult.textContent = text;
  reminderResult.classList.toggle('error', Boolean(isError));
  reminderResult.classList.toggle('success', !isError);
}

function renderOrder(order) {
  currentOrder = order;
  showReminderResult('', false);

  document.getElementById('orderId').textContent = order.order_id;
  document.getElementById('orderCreated').textContent = order.created_at;
  document.getElementById('orderUpdated').textContent = order.updated_at;

  const statusEl = document.getElementById('orderStatus');
  statusEl.textContent = order.status;
  statusEl.className = 'status-badge ' + statusClass(order.status);

  // Items
  const itemsEl = document.getElementById('orderItems');
  itemsEl.innerHTML = order.items.map(function(item) {
    return '\
      <div class="order-item">\
        <div class="item-info">\
          <div class="item-thumbnail">\
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">\
              <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>\
              <line x1="3" y1="6" x2="21" y2="6"/>\
              <path d="M16 10a4 4 0 0 1-8 0"/>\
            </svg>\
          </div>\
          <div class="item-text">\
            <div class="item-name">' + item.name + '</div>\
            <div class="item-sku">SKU: ' + item.sku + '</div>\
          </div>\
        </div>\
        <div class="item-detail">\
          <div class="item-price">' + fmtCurrency(item.price) + '</div>\
          <div class="item-qty">x' + item.quantity + '</div>\
        </div>\
      </div>';
  }).join('');

  // Totals
  const totalQty = order.items.reduce(function(s, i) { return s + i.quantity; }, 0);
  document.getElementById('totalQty').textContent = totalQty + ' 件';
  document.getElementById('totalAmount').textContent = fmtCurrency(order.total);

  // Customer
  document.getElementById('customerName').textContent = order.customer.name;
  document.getElementById('customerPhone').textContent = order.customer.phone;
  document.getElementById('customerEmail').textContent = order.customer.email;
  document.getElementById('paymentMethod').textContent = order.payment_method;

  // Shipping
  document.getElementById('shippingAddress').textContent = order.shipping.address;
  document.getElementById('shippingMethod').textContent = order.shipping.method;
  document.getElementById('trackingNo').textContent = order.shipping.tracking_no;

  // Timeline
  const timelineEl = document.getElementById('timeline');
  const events = order.timeline || [];
  const activeIndex = timelineActiveIndex(order);
  timelineEl.innerHTML = events.map(function(t, i) {
    const stateClass = i === activeIndex ? ' active' : '';
    return '\
      <div class="timeline-item' + stateClass + '">\
        <div class="timeline-dot"></div>\
        <div class="timeline-content">\
          <div class="event">' + t.event + '</div>\
          <div class="time">' + t.time + '</div>\
        </div>\
      </div>';
  }).join('');

  orderDetail.style.display = 'block';
  emptyState.style.display = 'none';
  // Smooth scroll to result
  orderDetail.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function searchOrder() {
  const orderId = input.value.trim();
  clearHint();
  if (!orderId) {
    showHint('请输入订单编号');
    return;
  }

  searchBtn.textContent = '查询中...';
  searchBtn.disabled = true;

  try {
    const res = await fetch('/api/order/' + encodeURIComponent(orderId));
    const data = await res.json();
    if (res.ok && data.success) {
      renderOrder(data.data);
    } else {
      showHint(data.message || '未找到该订单');
    }
  } catch (e) {
    showHint('查询失败，请稍后重试');
  } finally {
    searchBtn.textContent = '查询';
    searchBtn.disabled = false;
  }
}

async function sendReminder() {
  if (!currentOrder) return;

  const handler = handlerSelect.value;
  if (!handler) {
    showReminderResult('请选择处理者', true);
    return;
  }

  remindBtn.disabled = true;
  remindBtn.querySelector('span').textContent = '发送中';

  try {
    const res = await fetch('/api/reminders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        order_id: currentOrder.order_id,
        handler: handler
      })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showReminderResult('催办信息成功发送', false);
    } else {
      showReminderResult(data.message || '催办失败', true);
    }
  } catch (e) {
    showReminderResult('催办失败，请稍后重试', true);
  } finally {
    remindBtn.disabled = handlerSelect.options.length === 0;
    remindBtn.querySelector('span').textContent = '发送催办';
  }
}

searchBtn.addEventListener('click', searchOrder);
input.addEventListener('keydown', function(e) {
  if (e.key === 'Enter') searchOrder();
});
remindBtn.addEventListener('click', sendReminder);

// Load handler options for reminders
fetch('/api/handlers').then(function(r) { return r.json(); }).then(function(data) {
  if (data.success) {
    populateHandlers(data.data);
  } else {
    remindBtn.disabled = true;
  }
}).catch(function() {
  remindBtn.disabled = true;
});
