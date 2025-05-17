<template>
  <div class="container">
    <!-- Page Title -->
    <h1 class="title">Target Object Masking Generator</h1>

    <!-- Image Upload Section -->
    <div class="section">
      <label class="label">Upload an Image:</label>
      <input type="file" @change="handleImageUpload" />
    </div>

    <!-- Prompt Input Section -->
    <div class="section">
      <label class="label">Enter a Target Object to Mask (e.g., dog):</label>
      <input
        type="text"
        v-model="prompt"
        placeholder="Enter object keyword"
      />
    </div>

    <!-- Submit Button -->
    <div class="section">
      <button :disabled="loading" @click="submit">
        {{ loading ? "Processing..." : "Generate Masked Image" }}
      </button>
    </div>

    <!-- Result Display Section -->
    <div class="section" v-if="resultUrl">
      <label class="label">Masked Result:</label>
      <img :src="resultUrl" class="result-image" />
    </div>

    <!-- Error Display Section -->
    <div class="error" v-if="errorMsg">{{ errorMsg }}</div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      prompt: "", // User input keyword (e.g., "dog")
      imageFile: null, // Uploaded image file
      resultUrl: "", // Result image URL from backend
      loading: false, // Loading indicator
      errorMsg: "", // Error message if request fails
    };
  },
  methods: {
    // Handle image upload event and store file reference
    handleImageUpload(event) {
      const file = event.target.files[0];
      this.imageFile = file;
    },

    // Submit image and prompt to backend API for masking
    async submit() {
      if (!this.imageFile || !this.prompt) {
        this.errorMsg = "Please upload an image and enter a prompt.";
        return;
      }

      this.loading = true;
      this.errorMsg = "";
      this.resultUrl = "";

      try {
        const formData = new FormData();
        formData.append("file", this.imageFile);
        formData.append("prompt", this.prompt);

        // Send POST request to FastAPI backend
        const response = await fetch("http://localhost:8000/mask", {
          method: "POST",
          body: formData,
        });

        const data = await response.json();
        if (response.ok && data.result_url) {
          this.resultUrl = data.result_url;
        } else {
          this.errorMsg = data.error || "Failed to generate result.";
        }
      } catch (error) {
        this.errorMsg = "Error occurred during request.";
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.container {
  max-width: 600px;
  margin: 0 auto;
  padding: 30px 20px;
  font-family: Arial, sans-serif;
}

.title {
  text-align: center;
  font-size: 28px;
  margin-bottom: 20px;
}

.section {
  margin-bottom: 20px;
}

.label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
}

input[type="text"],
input[type="file"] {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 6px;
}

button {
  width: 100%;
  padding: 12px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
}

button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.result-image {
  max-width: 100%;
  border-radius: 10px;
  margin-top: 10px;
}

.error {
  color: red;
  text-align: center;
  margin-top: 10px;
}
</style>
