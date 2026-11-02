import os

def update_base_html():
    path = 'app/templates/base.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add CSS
    css_target = ".navbar {"
    css_addition = """        .user-avatar-circle img,
        .user-avatar-img {
            width: 100% !important;
            height: 100% !important;
            object-fit: cover !important;
            border-radius: 50% !important;
            display: block !important;
        }

        .user-dropdown-item-btn {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            padding: 0.75rem 1.15rem;
            font-size: 0.84rem;
            font-weight: 600;
            color: #002b49;
            text-decoration: none;
            background: transparent;
            border: none;
            width: 100%;
            text-align: left;
            cursor: pointer;
            transition: background-color 0.15s ease, color 0.15s ease;
            border-bottom: 1px solid #f1f5f9;
        }

        .user-dropdown-item-btn:hover {
            background-color: #f0f9ff;
            color: #00B7CD;
        }

        @keyframes modalPop {
            0% { transform: scale(0.95); opacity: 0; }
            100% { transform: scale(1); opacity: 1; }
        }

        .navbar {"""

    if css_target in content and ".user-dropdown-item-btn" not in content:
        content = content.replace(css_target, css_addition, 1)
        print("Added profile CSS to base.html")

    # 2. Add Modal HTML and Scripts right before </body>
    modal_html_and_js = """
    {% if current_user %}
    <!-- ==========================================================================
         GLOBAL USER PROFILE MODAL
         ========================================================================== -->
    <div class="clean-modal-overlay" id="modalUserProfile" style="display: none; position: fixed; inset: 0; background: rgba(15, 23, 42, 0.55); backdrop-filter: blur(4px); z-index: 99999; align-items: center; justify-content: center; padding: 1rem;">
        <div class="clean-modal-card" style="background: #ffffff; border-radius: 16px; width: 100%; max-width: 480px; box-shadow: 0 20px 40px rgba(0, 43, 73, 0.18); overflow: hidden; animation: modalPop 0.2s cubic-bezier(0.16, 1, 0.3, 1);">
            <!-- Modal Head -->
            <div style="padding: 1.25rem 1.5rem; border-bottom: 1px solid #f1f5f9; display: flex; align-items: center; justify-content: space-between; background: #ffffff;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <div style="width: 40px; height: 40px; border-radius: 10px; background: #f0f9ff; color: #00B7CD; display: flex; align-items: center; justify-content: center; font-size: 1.15rem; border: 1px solid #bae6fd;">
                        <i class="fa-solid fa-user-gear"></i>
                    </div>
                    <div>
                        <h3 style="font-size: 1.05rem; font-weight: 700; color: #002b49; margin: 0; line-height: 1.3;">
                            {% if current_user.role == 'staff' %}
                                Edit Profil Petugas
                            {% elif current_user.role in ('dh', 'gm') %}
                                Edit Profil Department Head
                            {% else %}
                                Edit Profil Administrator
                            {% endif %}
                        </h3>
                        <p style="font-size: 0.78rem; color: #64748b; margin: 0; margin-top: 2px;">
                            {% if current_user.role == 'staff' %}
                                Perbarui foto profil dan nama pengguna Anda
                            {% elif current_user.role in ('dh', 'gm') %}
                                Perbarui foto profil Department Head
                            {% else %}
                                Perbarui foto profil dan nama akun Administrator
                            {% endif %}
                        </p>
                    </div>
                </div>
                <button type="button" onclick="closeProfileModal()" style="background: transparent; border: none; font-size: 1.1rem; color: #94a3b8; cursor: pointer; padding: 0.25rem 0.5rem; border-radius: 6px; transition: color 0.15s;" onmouseover="this.style.color='#0f172a'" onmouseout="this.style.color='#94a3b8'">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>

            <!-- Modal Body Form -->
            <form id="formUserProfile" onsubmit="submitUserProfile(event)" enctype="multipart/form-data">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <input type="hidden" name="remove_avatar" id="profile_remove_avatar" value="false">

                <div style="padding: 1.5rem; display: flex; flex-direction: column; gap: 1.25rem;">
                    
                    <!-- Avatar Preview & Upload Area -->
                    <div style="display: flex; align-items: center; gap: 1.25rem; padding: 1rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px;">
                        <div style="position: relative; width: 72px; height: 72px; min-width: 72px; border-radius: 50%; overflow: hidden; background: #00B7CD; color: #ffffff; display: flex; align-items: center; justify-content: center; font-size: 1.6rem; font-weight: 700; box-shadow: 0 4px 12px rgba(0, 183, 205, 0.25); border: 3px solid #ffffff;">
                            <img id="profileAvatarPreview" src="{{ current_user.avatar if current_user and current_user.avatar else '' }}" alt="Avatar" style="width: 100%; height: 100%; object-fit: cover; display: {{ 'block' if current_user and current_user.avatar else 'none' }};">
                            <span id="profileAvatarFallback" style="display: {{ 'none' if current_user and current_user.avatar else 'inline-block' }}; font-family: 'Outfit', sans-serif;">
                                {{ (current_user.name[:2]|upper) if current_user and current_user.name else 'US' }}
                            </span>
                        </div>

                        <div style="flex: 1;">
                            <div style="font-size: 0.82rem; font-weight: 700; color: #002b49; margin-bottom: 0.35rem;">
                                Foto Profil
                            </div>
                            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                                <label for="profile_avatar_input" style="display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.4rem 0.85rem; background: #00B7CD; color: #ffffff; border-radius: 8px; font-size: 0.78rem; font-weight: 700; cursor: pointer; box-shadow: 0 2px 6px rgba(0, 183, 205, 0.25); transition: background 0.15s;" onmouseover="this.style.background='#009bb0'" onmouseout="this.style.background='#00B7CD'">
                                    <i class="fa-solid fa-camera"></i>
                                    <span>Pilih Foto</span>
                                </label>
                                <input type="file" id="profile_avatar_input" name="avatar" accept="image/png, image/jpeg, image/jpg, image/webp" style="display: none;" onchange="previewProfileAvatar(event)">

                                <button type="button" id="btnRemoveAvatar" onclick="handleRemoveAvatar()" style="display: {{ 'inline-flex' if current_user and current_user.avatar else 'none' }}; align-items: center; gap: 0.35rem; padding: 0.4rem 0.75rem; background: #ffffff; color: #ef4444; border: 1px solid #fca5a5; border-radius: 8px; font-size: 0.78rem; font-weight: 600; cursor: pointer;">
                                    <i class="fa-solid fa-trash-can"></i>
                                    <span>Hapus</span>
                                </button>
                            </div>
                            <small style="display: block; font-size: 0.72rem; color: #64748b; margin-top: 0.35rem;">PNG, JPG, atau WEBP (Maksimal 5MB)</small>
                        </div>
                    </div>

                    <!-- Field 1: Nama Pengguna (Display Name) -->
                    <div>
                        <label style="display: block; font-size: 0.82rem; font-weight: 700; color: #1e293b; margin-bottom: 0.4rem;">
                            Nama Pengguna
                            {% if current_user.role in ('staff', 'admin') %}
                                <span style="color: #ef4444;">*</span>
                            {% endif %}
                        </label>

                        {% if current_user.role in ('staff', 'admin') %}
                            <!-- BISA DIEDIT OLEH STAFF & ADMIN -->
                            <div style="position: relative;">
                                <i class="fa-solid fa-user" style="position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #94a3b8; font-size: 0.9rem;"></i>
                                <input type="text" id="profile_input_name" name="name" value="{{ current_user.name }}" required placeholder="Masukkan Nama Lengkap Anda" style="width: 100%; box-sizing: border-box; padding: 0.65rem 0.85rem 0.65rem 2.4rem; border: 1.5px solid #cbd5e1; border-radius: 10px; font-size: 0.88rem; font-weight: 600; color: #0f172a; outline: none; transition: border-color 0.15s, box-shadow 0.15s;" onfocus="this.style.borderColor='#00B7CD'; this.style.boxShadow='0 0 0 3px rgba(0, 183, 205, 0.15)';" onblur="this.style.borderColor='#cbd5e1'; this.style.boxShadow='none';">
                            </div>
                            <small style="display: block; font-size: 0.74rem; color: #64748b; margin-top: 0.35rem;">
                                {% if current_user.role == 'staff' %}
                                    Nama ini tercantum sebagai <strong>Petugas Pengirim</strong> pada dokumen dan laporan resmi.
                                {% else %}
                                    Nama tampilan identitas Administrator Regional II.
                                {% endif %}
                            </small>
                        {% else %}
                            <!-- TERKUNCI UNTUK DEPARTMENT HEAD -->
                            <div style="position: relative;">
                                <i class="fa-solid fa-lock" style="position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #94a3b8; font-size: 0.9rem;"></i>
                                <input type="text" value="{{ current_user.name }}" disabled style="width: 100%; box-sizing: border-box; padding: 0.65rem 0.85rem 0.65rem 2.4rem; border: 1.5px solid #e2e8f0; background: #f8fafc; border-radius: 10px; font-size: 0.88rem; font-weight: 600; color: #64748b; cursor: not-allowed;">
                            </div>
                            <small style="display: block; font-size: 0.74rem; color: #64748b; margin-top: 0.35rem;">
                                <i class="fa-solid fa-lock me-1"></i> Nama Department Head bersifat kedinasan dan dikelola oleh Administrator.
                            </small>
                        {% endif %}
                    </div>

                    <!-- Field 2: Nama Akun (Username Login) -->
                    <div>
                        <label style="display: block; font-size: 0.82rem; font-weight: 700; color: #1e293b; margin-bottom: 0.4rem;">
                            Nama Akun (Username Login)
                        </label>
                        <div style="position: relative;">
                            <i class="fa-solid fa-at" style="position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #94a3b8; font-size: 0.9rem;"></i>
                            <input type="text" value="{{ current_user.username }}" disabled style="width: 100%; box-sizing: border-box; padding: 0.65rem 0.85rem 0.65rem 2.4rem; border: 1.5px solid #e2e8f0; background: #f8fafc; border-radius: 10px; font-size: 0.88rem; font-family: monospace; font-weight: 600; color: #64748b; cursor: not-allowed;">
                        </div>
                        <small style="display: block; font-size: 0.74rem; color: #64748b; margin-top: 0.35rem;">
                            <i class="fa-solid fa-lock me-1"></i> Nama akun login kedinasan tidak dapat diubah secara mandiri.
                        </small>
                    </div>

                    <!-- Field 3: Info Peran & Cabang -->
                    <div style="display: flex; gap: 0.75rem;">
                        <div style="flex: 1; padding: 0.6rem 0.85rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;">
                            <span style="display: block; font-size: 0.68rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Peran Akun</span>
                            <strong style="font-size: 0.82rem; color: #002b49;">
                                {% if current_user.role == 'staff' %}Petugas Lapangan (Staff)
                                {% elif current_user.role in ('dh', 'gm') %}Department Head (DH)
                                {% else %}Administrator Regional II{% endif %}
                            </strong>
                        </div>
                        {% if current_user.airport %}
                        <div style="flex: 1; padding: 0.6rem 0.85rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;">
                            <span style="display: block; font-size: 0.68rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Cabang Penugasan</span>
                            <strong style="font-size: 0.82rem; color: #002b49;">Cabang {{ current_user.airport }}</strong>
                        </div>
                        {% endif %}
                    </div>

                </div>

                <!-- Modal Footer -->
                <div style="padding: 1rem 1.5rem; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 0.75rem;">
                    <button type="button" onclick="closeProfileModal()" style="padding: 0.55rem 1.25rem; background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 10px; font-size: 0.85rem; font-weight: 700; color: #475569; cursor: pointer;">
                        Batal
                    </button>
                    <button type="submit" id="btnSaveProfile" style="padding: 0.55rem 1.5rem; background: #00B7CD; border: none; border-radius: 10px; font-size: 0.85rem; font-weight: 700; color: #ffffff; cursor: pointer; display: inline-flex; align-items: center; gap: 0.4rem; box-shadow: 0 2px 8px rgba(0, 183, 205, 0.25);">
                        <i class="fa-solid fa-floppy-disk"></i>
                        <span>Simpan Perubahan</span>
                    </button>
                </div>
            </form>
        </div>
    </div>

    <!-- Script Controller Profile Modal -->
    <script>
        window.openProfileModal = function() {
            const modal = document.getElementById('modalUserProfile');
            if (modal) {
                modal.style.display = 'flex';
                const fileInp = document.getElementById('profile_avatar_input');
                if (fileInp) fileInp.value = '';
                const removeFlag = document.getElementById('profile_remove_avatar');
                if (removeFlag) removeFlag.value = 'false';
            }
        };

        window.closeProfileModal = function() {
            const modal = document.getElementById('modalUserProfile');
            if (modal) modal.style.display = 'none';
        };

        window.previewProfileAvatar = function(e) {
            const file = e.target.files[0];
            if (!file) return;
            if (file.size > 5 * 1024 * 1024) {
                Swal.fire('File Terlalu Besar', 'Ukuran foto maksimal adalah 5MB.', 'warning');
                e.target.value = '';
                return;
            }
            const reader = new FileReader();
            reader.onload = function(evt) {
                const img = document.getElementById('profileAvatarPreview');
                const fallback = document.getElementById('profileAvatarFallback');
                const btnRemove = document.getElementById('btnRemoveAvatar');
                const removeFlag = document.getElementById('profile_remove_avatar');
                if (img) {
                    img.src = evt.target.result;
                    img.style.display = 'block';
                }
                if (fallback) fallback.style.display = 'none';
                if (btnRemove) btnRemove.style.display = 'inline-flex';
                if (removeFlag) removeFlag.value = 'false';
            };
            reader.readAsDataURL(file);
        };

        window.handleRemoveAvatar = function() {
            const img = document.getElementById('profileAvatarPreview');
            const fallback = document.getElementById('profileAvatarFallback');
            const btnRemove = document.getElementById('btnRemoveAvatar');
            const fileInp = document.getElementById('profile_avatar_input');
            const removeFlag = document.getElementById('profile_remove_avatar');
            if (img) {
                img.src = '';
                img.style.display = 'none';
            }
            if (fallback) fallback.style.display = 'inline-block';
            if (btnRemove) btnRemove.style.display = 'none';
            if (fileInp) fileInp.value = '';
            if (removeFlag) removeFlag.value = 'true';
        };

        window.submitUserProfile = function(e) {
            e.preventDefault();
            const form = document.getElementById('formUserProfile');
            if (!form) return;
            const btnSave = document.getElementById('btnSaveProfile');
            const origHtml = btnSave ? btnSave.innerHTML : 'Simpan Perubahan';
            if (btnSave) {
                btnSave.disabled = true;
                btnSave.innerHTML = '<span class="kawung-inline-spin me-2"></span> Menyimpan...';
            }
            const formData = new FormData(form);

            fetch('/api/user/profile', {
                method: 'POST',
                body: formData
            })
            .then(r => r.json())
            .then(res => {
                if (btnSave) {
                    btnSave.disabled = false;
                    btnSave.innerHTML = origHtml;
                }
                if (res.success) {
                    Swal.fire({
                        icon: 'success',
                        title: 'Profil Berhasil Diperbarui',
                        text: res.message || 'Perubahan profil Anda telah berhasil disimpan.',
                        confirmButtonColor: '#00B7CD'
                    }).then(() => {
                        window.location.reload();
                    });
                } else {
                    Swal.fire('Gagal Menyimpan', res.error || 'Terjadi kesalahan saat memperbarui profil.', 'error');
                }
            })
            .catch(err => {
                if (btnSave) {
                    btnSave.disabled = false;
                    btnSave.innerHTML = origHtml;
                }
                Swal.fire('Kesalahan Jaringan', err.message || 'Gagal terhubung ke server.', 'error');
            });
        };
    </script>
    {% endif %}
"""

    if "modalUserProfile" not in content:
        content = content.replace("</body>", modal_html_and_js + "\n</body>")
        print("Added modalUserProfile to base.html")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def update_staff_dashboard():
    path = 'app/templates/staff_dashboard.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update avatar in topbar
    old_avatar = """                <div class="user-avatar-circle">
                    {{ (current_user.name[:2]|upper) if current_user.name else 'MH' }}
                </div>"""

    new_avatar = """                <div class="user-avatar-circle">
                    {% if current_user and current_user.avatar %}
                        <img src="{{ current_user.avatar }}" alt="Avatar" class="user-avatar-img">
                    {% else %}
                        {{ (current_user.name[:2]|upper) if current_user and current_user.name else 'MH' }}
                    {% endif %}
                </div>"""

    if old_avatar in content:
        content = content.replace(old_avatar, new_avatar)
        print("Updated avatar in staff_dashboard.html")

    # 2. Add Edit Profil button in dropdown
    old_logout = """                    <a href="/api/auth/logout" class="user-dropdown-link">
                        <i class="fa-solid fa-arrow-right-from-bracket"></i>
                        <span>Keluar dari Sistem</span>
                    </a>"""

    new_logout = """                    <button type="button" class="user-dropdown-item-btn" onclick="openProfileModal(); event.stopPropagation();">
                        <i class="fa-solid fa-user-pen" style="color: #00B7CD;"></i>
                        <span>Edit Profil</span>
                    </button>
                    <a href="/api/auth/logout" class="user-dropdown-link">
                        <i class="fa-solid fa-arrow-right-from-bracket"></i>
                        <span>Keluar dari Sistem</span>
                    </a>"""

    if old_logout in content and "openProfileModal" not in content:
        content = content.replace(old_logout, new_logout)
        print("Added Edit Profil button in staff_dashboard.html")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def update_gm_dashboard():
    path = 'app/templates/gm_dashboard.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update avatar in topbar
    old_avatar = """                <div class="user-avatar-circle">
                    {{ (current_user.name[:2]|upper) if current_user.name else 'DH' }}
                </div>"""

    new_avatar = """                <div class="user-avatar-circle">
                    {% if current_user and current_user.avatar %}
                        <img src="{{ current_user.avatar }}" alt="Avatar" class="user-avatar-img">
                    {% else %}
                        {{ (current_user.name[:2]|upper) if current_user and current_user.name else 'DH' }}
                    {% endif %}
                </div>"""

    if old_avatar in content:
        content = content.replace(old_avatar, new_avatar)
        print("Updated avatar in gm_dashboard.html")

    # 2. Add Edit Profil button in dropdown
    old_logout = """                    <a href="/api/auth/logout" class="user-dropdown-link">
                        <i class="fa-solid fa-arrow-right-from-bracket"></i>
                        <span>Keluar dari Sistem</span>
                    </a>"""

    new_logout = """                    <button type="button" class="user-dropdown-item-btn" onclick="openProfileModal(); event.stopPropagation();">
                        <i class="fa-solid fa-user-pen" style="color: #00B7CD;"></i>
                        <span>Edit Profil</span>
                    </button>
                    <a href="/api/auth/logout" class="user-dropdown-link">
                        <i class="fa-solid fa-arrow-right-from-bracket"></i>
                        <span>Keluar dari Sistem</span>
                    </a>"""

    if old_logout in content and "openProfileModal" not in content:
        content = content.replace(old_logout, new_logout)
        print("Added Edit Profil button in gm_dashboard.html")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def update_admin_dashboard():
    path = 'app/templates/admin_dashboard.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update avatar in topbar
    old_avatar = """                        <div class="user-avatar-circle">
                            {{ (current_user.name[:2]|upper) if current_user and current_user.name else 'AR' }}
                        </div>"""

    new_avatar = """                        <div class="user-avatar-circle">
                            {% if current_user and current_user.avatar %}
                                <img src="{{ current_user.avatar }}" alt="Avatar" class="user-avatar-img">
                            {% else %}
                                {{ (current_user.name[:2]|upper) if current_user and current_user.name else 'AR' }}
                            {% endif %}
                        </div>"""

    if old_avatar in content:
        content = content.replace(old_avatar, new_avatar)
        print("Updated avatar in admin_dashboard.html")

    # 2. Add Edit Profil button in dropdown
    old_logout = """                            <a href="/api/auth/logout" class="user-dropdown-link">
                                <i class="fa-solid fa-arrow-right-from-bracket"></i>
                                <span>Keluar dari Sistem</span>
                            </a>"""

    new_logout = """                            <button type="button" class="user-dropdown-item-btn" onclick="openProfileModal(); event.stopPropagation();">
                                <i class="fa-solid fa-user-pen" style="color: #00B7CD;"></i>
                                <span>Edit Profil</span>
                            </button>
                            <a href="/api/auth/logout" class="user-dropdown-link">
                                <i class="fa-solid fa-arrow-right-from-bracket"></i>
                                <span>Keluar dari Sistem</span>
                            </a>"""

    if old_logout in content and "openProfileModal" not in content:
        content = content.replace(old_logout, new_logout)
        print("Added Edit Profil button in admin_dashboard.html")

    # 3. In renderUsersTable, render avatar image if present
    old_cell_avatar = """                            <div class="user-cell-avatar ${avatarClass}">
                                ${escapeHtml(initials)}
                            </div>"""

    new_cell_avatar = """                            <div class="user-cell-avatar ${avatarClass}">
                                ${u.avatar ? `<img src="${escapeHtml(u.avatar)}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">` : escapeHtml(initials)}
                            </div>"""

    if old_cell_avatar in content:
        content = content.replace(old_cell_avatar, new_cell_avatar)
        print("Updated user cell avatar in admin_dashboard.html")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    update_base_html()
    update_staff_dashboard()
    update_gm_dashboard()
    update_admin_dashboard()
    print("All profile features added successfully!")

