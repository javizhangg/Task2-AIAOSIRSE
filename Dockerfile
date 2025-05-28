# Use an official Miniconda image as the base
FROM continuumio/miniconda3:latest

# Set the working directory inside the container
WORKDIR /app

# Copy all project files into the container
COPY . .

# Install necessary system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create the conda environment based on environment.yml
RUN conda env create -f environment.yml

# Switch to bash so that PATH changes apply
SHELL ["conda", "run", "-n", "mi_entorno", "/bin/bash", "-c"]

# Prepend the new env to PATH so python, pip, etc. come from mi_entorno
ENV PATH=/opt/conda/envs/mi_entorno/bin:$PATH

RUN python - <<EOF
from sentence_transformers import SentenceTransformer
SentenceTransformer('all-MiniLM-L6-v2')
EOF

# Make sure your orchestration script is executable
RUN chmod +x execute.sh

# Expose your application ports
EXPOSE 8501 8070 8071 5000

# Final launch: run your pipeline and then Streamlit
CMD ["bash", "-c", "./execute.sh"]
