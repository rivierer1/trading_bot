document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('api-settings-form');
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Collect form data
        const formData = new FormData(form);
        const settings = {};
        
        // Convert FormData to object and validate
        for (let [key, value] of formData.entries()) {
            // Only include non-empty values
            if (value && value.trim() !== '') {
                settings[key] = value.trim();
            }
        }
        
        console.log('Submitting settings:', settings);  // Debug log
        
        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings)
            });
            
            const result = await response.json();
            console.log('Server response:', result);  // Debug log
            
            if (response.ok && result.status === 'success') {
                // Update form values with the returned config
                if (result.config) {
                    console.log('Updating form with new config:', result.config);  // Debug log
                    Object.entries(result.config).forEach(([key, value]) => {
                        const input = form.querySelector(`[name="${key}"]`);
                        if (input) {
                            input.value = value || '';
                            console.log(`Updated ${key} with value:`, value);  // Debug log
                        } else {
                            console.log(`No input found for ${key}`);  // Debug log
                        }
                    });
                }
                
                alert('Settings saved successfully!');
            } else {
                throw new Error(result.message || 'Failed to save settings');
            }
        } catch (error) {
            console.error('Error:', error);
            alert(`Error saving settings: ${error.message}`);
        }
    });

    // Add show/hide password functionality
    document.querySelectorAll('input[type="password"]').forEach(input => {
        const container = input.parentElement;
        
        // Create and append toggle button
        const toggleButton = document.createElement('button');
        toggleButton.type = 'button';
        toggleButton.className = 'btn btn-outline-secondary btn-sm float-end';
        toggleButton.style.marginTop = '-38px';
        toggleButton.style.marginRight = '10px';
        toggleButton.innerHTML = '<i class="fas fa-eye"></i>';
        container.appendChild(toggleButton);
        
        // Add click handler
        toggleButton.addEventListener('click', () => {
            if (input.type === 'password') {
                input.type = 'text';
                toggleButton.innerHTML = '<i class="fas fa-eye-slash"></i>';
            } else {
                input.type = 'password';
                toggleButton.innerHTML = '<i class="fas fa-eye"></i>';
            }
        });
    });
});
