// Cart functionality
let cart = JSON.parse(localStorage.getItem('cart')) || [];

// Update cart count
function updateCartCount() {
    const cartCount = document.querySelector('.cart-count');
    if (cartCount) {
        const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
        cartCount.textContent = totalItems;
    }
}

// Add to cart functionality
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('add-to-cart')) {
        const button = e.target;
        const menuItem = button.closest('.menu-item');
        
        if (menuItem) {
            const itemId = menuItem.dataset.id;
            const itemName = menuItem.querySelector('h3').textContent.replace('🌱', '').trim();
            const weightSelect = menuItem.querySelector('.weight-select');
            const weight = weightSelect.options[weightSelect.selectedIndex].text;
            const weightValue = weightSelect.value;
            const basePrice = parseInt(weightSelect.options[weightSelect.selectedIndex].dataset.price);
            const itemImage = menuItem.querySelector('img') ? menuItem.querySelector('img').src : '';
            
            // Check if item already in cart
            const existingItem = cart.find(item => 
                item.id === itemId && item.weight === weightValue
            );
            
            if (existingItem) {
                existingItem.quantity += 1;
            } else {
                cart.push({
                    id: itemId,
                    name: itemName,
                    weight: weightValue,
                    weightText: weight,
                    price: basePrice,
                    image: itemImage,
                    quantity: 1
                });
            }
            
            // Save to localStorage
            localStorage.setItem('cart', JSON.stringify(cart));
            
            // Update cart count
            updateCartCount();
            
            // Show animation
            button.textContent = 'Added! ✓';
            button.style.background = '#D2691E';
            setTimeout(() => {
                button.textContent = 'Add to Cart';
                button.style.background = '';
            }, 1000);
            
            // Show notification
            showNotification('Item added to cart!');
        }
    }
});

// Cart page functionality
function renderCartPage() {
    const cartContainer = document.querySelector('.cart-items');
    const subtotalElement = document.querySelector('.subtotal');
    const deliveryFee = 40;
    const totalElement = document.querySelector('.total-amount');
    
    if (cartContainer) {
        if (cart.length === 0) {
            cartContainer.innerHTML = `
                <div class="empty-cart">
                    <i class="fas fa-shopping-cart"></i>
                    <p>Your cart is empty</p>
                    <a href="/menu" class="btn btn-primary">Browse Menu</a>
                </div>
            `;
            if (subtotalElement) subtotalElement.textContent = '₹0';
            if (totalElement) totalElement.textContent = '₹0';
            return;
        }
        
        let cartHTML = '';
        let subtotal = 0;
        
        cart.forEach((item, index) => {
            const itemTotal = item.price * item.quantity;
            subtotal += itemTotal;
            
            cartHTML += `
                <div class="cart-item" data-index="${index}">
                    <img src="${item.image || 'https://via.placeholder.com/80'}" alt="${item.name}">
                    <div class="cart-item-details">
                        <h4>${item.name}</h4>
                        <p>${item.weightText || ''}</p>
                    </div>
                    <div class="cart-item-price">₹${itemTotal}</div>
                    <div class="cart-item-actions">
                        <button class="quantity-btn minus" data-index="${index}">-</button>
                        <span class="quantity">${item.quantity}</span>
                        <button class="quantity-btn plus" data-index="${index}">+</button>
                        <i class="fas fa-trash remove-item" data-index="${index}"></i>
                    </div>
                </div>
            `;
        });
        
        cartContainer.innerHTML = cartHTML;
        
        const total = subtotal + deliveryFee;
        
        if (subtotalElement) subtotalElement.textContent = `₹${subtotal}`;
        if (totalElement) totalElement.textContent = `₹${total}`;
        
        // Add event listeners for cart actions
        attachCartActions();
    }
}

// Attach cart action listeners
function attachCartActions() {
    // Plus button
    document.querySelectorAll('.quantity-btn.plus').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = e.target.dataset.index;
            cart[index].quantity += 1;
            localStorage.setItem('cart', JSON.stringify(cart));
            renderCartPage();
            updateCartCount();
        });
    });
    
    // Minus button
    document.querySelectorAll('.quantity-btn.minus').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = e.target.dataset.index;
            if (cart[index].quantity > 1) {
                cart[index].quantity -= 1;
            } else {
                cart.splice(index, 1);
            }
            localStorage.setItem('cart', JSON.stringify(cart));
            renderCartPage();
            updateCartCount();
        });
    });
    
    // Remove button
    document.querySelectorAll('.remove-item').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = e.target.dataset.index;
            cart.splice(index, 1);
            localStorage.setItem('cart', JSON.stringify(cart));
            renderCartPage();
            updateCartCount();
            showNotification('Item removed from cart');
        });
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    updateCartCount();
    
    // Render cart page if on cart page
    if (window.location.pathname.includes('cart')) {
        renderCartPage();
    }
});