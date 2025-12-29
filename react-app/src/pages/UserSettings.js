import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import Navigation from '../components/Navigation';

const UserSettings = () => {
  const { user, updateUser } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: user?.name || '',
    email: user?.email || '',
    bio: user?.bio || '',
    location: user?.location || '',
    website: user?.website || ''
  });

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    updateUser(formData);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setFormData({
      name: user?.name || '',
      email: user?.email || '',
      bio: user?.bio || '',
      location: user?.location || '',
      website: user?.website || ''
    });
    setIsEditing(false);
  };

  return (
    <div style={styles.container}>
      <Navigation />
      <div style={styles.content}>
        <div style={styles.header}>
          <h1 style={styles.title}>User Settings</h1>
          <p style={styles.subtitle}>Manage your account settings and preferences</p>
        </div>

        <div style={styles.settingsCard}>
          <div style={styles.profileSection}>
            <img 
              src={user?.picture || 'https://via.placeholder.com/100'} 
              alt="Profile" 
              style={styles.profileImage}
            />
            <div style={styles.profileInfo}>
              <h2 style={styles.profileName}>{user?.name}</h2>
              <p style={styles.profileEmail}>{user?.email}</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} style={styles.form}>
            <div style={styles.formSection}>
              <h3 style={styles.sectionTitle}>Personal Information</h3>
              
              <div style={styles.formGroup}>
                <label style={styles.label}>Full Name</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  disabled={!isEditing}
                  style={isEditing ? styles.input : styles.inputDisabled}
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Email Address</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  disabled={true}
                  style={styles.inputDisabled}
                />
                <p style={styles.helpText}>Email cannot be changed (linked to Google account)</p>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Bio</label>
                <textarea
                  name="bio"
                  value={formData.bio}
                  onChange={handleChange}
                  disabled={!isEditing}
                  rows="4"
                  placeholder="Tell us about yourself..."
                  style={isEditing ? styles.textarea : styles.textareaDisabled}
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Location</label>
                <input
                  type="text"
                  name="location"
                  value={formData.location}
                  onChange={handleChange}
                  disabled={!isEditing}
                  placeholder="City, Country"
                  style={isEditing ? styles.input : styles.inputDisabled}
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Website</label>
                <input
                  type="url"
                  name="website"
                  value={formData.website}
                  onChange={handleChange}
                  disabled={!isEditing}
                  placeholder="https://example.com"
                  style={isEditing ? styles.input : styles.inputDisabled}
                />
              </div>
            </div>

            <div style={styles.buttonGroup}>
              {!isEditing ? (
                <button 
                  type="button"
                  onClick={() => setIsEditing(true)} 
                  style={styles.editButton}
                >
                  Edit Profile
                </button>
              ) : (
                <>
                  <button type="submit" style={styles.saveButton}>
                    Save Changes
                  </button>
                  <button 
                    type="button"
                    onClick={handleCancel} 
                    style={styles.cancelButton}
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>
          </form>

          <div style={styles.dangerZone}>
            <h3 style={styles.dangerTitle}>Danger Zone</h3>
            <p style={styles.dangerText}>
              Once you delete your account, there is no going back. Please be certain.
            </p>
            <button style={styles.deleteButton}>
              Delete Account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    background: '#f5f7fa'
  },
  content: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '20px'
  },
  header: {
    marginBottom: '30px'
  },
  title: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#333',
    marginBottom: '5px'
  },
  subtitle: {
    fontSize: '16px',
    color: '#666'
  },
  settingsCard: {
    background: 'white',
    borderRadius: '12px',
    padding: '30px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)'
  },
  profileSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '20px',
    marginBottom: '30px',
    paddingBottom: '30px',
    borderBottom: '1px solid #e0e0e0'
  },
  profileImage: {
    width: '100px',
    height: '100px',
    borderRadius: '50%',
    objectFit: 'cover',
    border: '3px solid #667eea'
  },
  profileInfo: {
    flex: 1
  },
  profileName: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#333',
    marginBottom: '5px'
  },
  profileEmail: {
    fontSize: '16px',
    color: '#666'
  },
  form: {
    marginBottom: '30px'
  },
  formSection: {
    marginBottom: '30px'
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#333',
    marginBottom: '20px'
  },
  formGroup: {
    marginBottom: '20px'
  },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: '600',
    color: '#333',
    marginBottom: '8px'
  },
  input: {
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    border: '2px solid #e0e0e0',
    borderRadius: '8px',
    outline: 'none',
    transition: 'border-color 0.2s',
    boxSizing: 'border-box'
  },
  inputDisabled: {
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    border: '2px solid #f0f0f0',
    borderRadius: '8px',
    background: '#f9f9f9',
    color: '#999',
    cursor: 'not-allowed',
    boxSizing: 'border-box'
  },
  textarea: {
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    border: '2px solid #e0e0e0',
    borderRadius: '8px',
    outline: 'none',
    resize: 'vertical',
    fontFamily: 'inherit',
    transition: 'border-color 0.2s',
    boxSizing: 'border-box'
  },
  textareaDisabled: {
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    border: '2px solid #f0f0f0',
    borderRadius: '8px',
    background: '#f9f9f9',
    color: '#999',
    cursor: 'not-allowed',
    resize: 'vertical',
    fontFamily: 'inherit',
    boxSizing: 'border-box'
  },
  helpText: {
    fontSize: '12px',
    color: '#999',
    marginTop: '5px'
  },
  buttonGroup: {
    display: 'flex',
    gap: '15px',
    justifyContent: 'flex-end'
  },
  editButton: {
    padding: '12px 30px',
    fontSize: '16px',
    fontWeight: '600',
    color: 'white',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s',
    boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)'
  },
  saveButton: {
    padding: '12px 30px',
    fontSize: '16px',
    fontWeight: '600',
    color: 'white',
    background: '#10b981',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s'
  },
  cancelButton: {
    padding: '12px 30px',
    fontSize: '16px',
    fontWeight: '600',
    color: '#666',
    background: '#f0f0f0',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s'
  },
  dangerZone: {
    paddingTop: '30px',
    borderTop: '1px solid #e0e0e0'
  },
  dangerTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#dc2626',
    marginBottom: '10px'
  },
  dangerText: {
    fontSize: '14px',
    color: '#666',
    marginBottom: '15px'
  },
  deleteButton: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: '600',
    color: 'white',
    background: '#dc2626',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s'
  }
};

export default UserSettings;
