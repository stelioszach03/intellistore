package main

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/intellistore/core/pkg/erasure"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"go.uber.org/zap"
)

var (
	logger    *zap.Logger
	apiURL    string
	vaultAddr string
	vaultToken string
	configFile string
)

func main() {
	var err error
	logger, err = zap.NewProduction()
	if err != nil {
		fmt.Printf("Failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer logger.Sync()

	rootCmd := &cobra.Command{
		Use:   "intellistore-client",
		Short: "IntelliStore CLI client",
		Long:  "Command-line interface for IntelliStore distributed object storage",
	}

	// Global flags
	rootCmd.PersistentFlags().StringVar(&configFile, "config", "", "config file (default is $HOME/.intellistore.yaml)")
	rootCmd.PersistentFlags().StringVar(&apiURL, "api-url", "http://localhost:8000", "IntelliStore API URL")
	rootCmd.PersistentFlags().StringVar(&vaultAddr, "vault-addr", "http://localhost:8200", "Vault address")
	rootCmd.PersistentFlags().StringVar(&vaultToken, "vault-token", "", "Vault token")

	// Initialize config
	cobra.OnInitialize(initConfig)

	// Add commands
	rootCmd.AddCommand(
		newLoginCmd(),
		newBucketCmd(),
		newObjectCmd(),
		newConfigCmd(),
	)

	if err := rootCmd.Execute(); err != nil {
		logger.Error("Command execution failed", zap.Error(err))
		os.Exit(1)
	}
}

func initConfig() {
	if configFile != "" {
		viper.SetConfigFile(configFile)
	} else {
		home, err := os.UserHomeDir()
		if err != nil {
			logger.Error("Failed to get home directory", zap.Error(err))
			return
		}

		viper.AddConfigPath(home)
		viper.SetConfigName(".intellistore")
		viper.SetConfigType("yaml")
	}

	viper.AutomaticEnv()

	if err := viper.ReadInConfig(); err == nil {
		logger.Info("Using config file", zap.String("file", viper.ConfigFileUsed()))
	}

	// Override with command line flags
	if apiURL == "" {
		apiURL = viper.GetString("api-url")
	}
	if vaultAddr == "" {
		vaultAddr = viper.GetString("vault-addr")
	}
	if vaultToken == "" {
		vaultToken = viper.GetString("vault-token")
	}
}

func newLoginCmd() *cobra.Command {
	var username, password string

	cmd := &cobra.Command{
		Use:   "login",
		Short: "Login to IntelliStore",
		RunE: func(cmd *cobra.Command, args []string) error {
			if username == "" {
				fmt.Print("Username: ")
				fmt.Scanln(&username)
			}
			if password == "" {
				fmt.Print("Password: ")
				fmt.Scanln(&password)
			}

			return login(username, password)
		},
	}

	cmd.Flags().StringVarP(&username, "username", "u", "", "Username")
	cmd.Flags().StringVarP(&password, "password", "p", "", "Password")

	return cmd
}

func newBucketCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "bucket",
		Short: "Bucket operations",
	}

	cmd.AddCommand(
		&cobra.Command{
			Use:   "create <bucket-name>",
			Short: "Create a new bucket",
			Args:  cobra.ExactArgs(1),
			RunE: func(cmd *cobra.Command, args []string) error {
				return createBucket(args[0])
			},
		},
		&cobra.Command{
			Use:   "delete <bucket-name>",
			Short: "Delete a bucket",
			Args:  cobra.ExactArgs(1),
			RunE: func(cmd *cobra.Command, args []string) error {
				return deleteBucket(args[0])
			},
		},
		&cobra.Command{
			Use:   "list",
			Short: "List buckets",
			RunE: func(cmd *cobra.Command, args []string) error {
				return listBuckets()
			},
		},
	)

	return cmd
}

func newObjectCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "object",
		Short: "Object operations",
	}

	var tier string
	uploadCmd := &cobra.Command{
		Use:   "upload <bucket-name> <object-key> <file-path>",
		Short: "Upload an object",
		Args:  cobra.ExactArgs(3),
		RunE: func(cmd *cobra.Command, args []string) error {
			return uploadObject(args[0], args[1], args[2], tier)
		},
	}
	uploadCmd.Flags().StringVar(&tier, "tier", "hot", "Storage tier (hot/cold)")

	cmd.AddCommand(
		uploadCmd,
		&cobra.Command{
			Use:   "download <bucket-name> <object-key> <output-path>",
			Short: "Download an object",
			Args:  cobra.ExactArgs(3),
			RunE: func(cmd *cobra.Command, args []string) error {
				return downloadObject(args[0], args[1], args[2])
			},
		},
		&cobra.Command{
			Use:   "delete <bucket-name> <object-key>",
			Short: "Delete an object",
			Args:  cobra.ExactArgs(2),
			RunE: func(cmd *cobra.Command, args []string) error {
				return deleteObject(args[0], args[1])
			},
		},
		&cobra.Command{
			Use:   "list <bucket-name>",
			Short: "List objects in a bucket",
			Args:  cobra.ExactArgs(1),
			RunE: func(cmd *cobra.Command, args []string) error {
				return listObjects(args[0])
			},
		},
		&cobra.Command{
			Use:   "migrate-tier <bucket-name> <object-key> <new-tier>",
			Short: "Migrate object to different tier",
			Args:  cobra.ExactArgs(3),
			RunE: func(cmd *cobra.Command, args []string) error {
				return migrateTier(args[0], args[1], args[2])
			},
		},
	)

	return cmd
}

func newConfigCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "config",
		Short: "Configuration management",
	}

	cmd.AddCommand(
		&cobra.Command{
			Use:   "set <key> <value>",
			Short: "Set configuration value",
			Args:  cobra.ExactArgs(2),
			RunE: func(cmd *cobra.Command, args []string) error {
				viper.Set(args[0], args[1])
				return viper.WriteConfig()
			},
		},
		&cobra.Command{
			Use:   "get <key>",
			Short: "Get configuration value",
			Args:  cobra.ExactArgs(1),
			RunE: func(cmd *cobra.Command, args []string) error {
				fmt.Println(viper.Get(args[0]))
				return nil
			},
		},
	)

	return cmd
}

func login(username, password string) error {
	loginData := map[string]string{
		"username": username,
		"password": password,
	}

	jsonData, err := json.Marshal(loginData)
	if err != nil {
		return fmt.Errorf("failed to marshal login data: %w", err)
	}

	resp, err := http.Post(apiURL+"/auth/login", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to login: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("login failed with status: %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return fmt.Errorf("failed to decode response: %w", err)
	}

	if token, ok := result["token"].(string); ok {
		viper.Set("auth-token", token)
		viper.WriteConfig()
		fmt.Println("Login successful")
	}

	return nil
}

func createBucket(bucketName string) error {
	bucketData := map[string]interface{}{
		"name":  bucketName,
		"owner": viper.GetString("username"),
	}

	return makeAPIRequest("POST", "/buckets", bucketData, nil)
}

func deleteBucket(bucketName string) error {
	return makeAPIRequest("DELETE", "/buckets/"+bucketName, nil, nil)
}

func listBuckets() error {
	var buckets []map[string]interface{}
	if err := makeAPIRequest("GET", "/buckets", nil, &buckets); err != nil {
		return err
	}

	fmt.Printf("%-20s %-10s %-15s %-20s\n", "NAME", "OBJECTS", "SIZE", "CREATED")
	fmt.Println(strings.Repeat("-", 70))

	for _, bucket := range buckets {
		name := bucket["name"].(string)
		objectCount := int(bucket["objectCount"].(float64))
		totalSize := int64(bucket["totalSize"].(float64))
		createdAt := bucket["createdAt"].(string)

		fmt.Printf("%-20s %-10d %-15s %-20s\n",
			name, objectCount, formatBytes(totalSize), createdAt)
	}

	return nil
}

func uploadObject(bucketName, objectKey, filePath, tier string) error {
	// Read file
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	data, err := io.ReadAll(file)
	if err != nil {
		return fmt.Errorf("failed to read file: %w", err)
	}

	logger.Info("Starting upload",
		zap.String("bucket", bucketName),
		zap.String("key", objectKey),
		zap.Int("size", len(data)))

	// Get encryption key from Vault
	encryptionKey, err := getEncryptionKey(bucketName, objectKey)
	if err != nil {
		return fmt.Errorf("failed to get encryption key: %w", err)
	}

	// Encrypt data
	encryptedData, err := encryptData(data, encryptionKey)
	if err != nil {
		return fmt.Errorf("failed to encrypt data: %w", err)
	}

	// Create erasure encoder
	encoder, err := erasure.NewDefaultEncoder()
	if err != nil {
		return fmt.Errorf("failed to create encoder: %w", err)
	}

	// Encode data into shards
	shards, err := encoder.EncodeData(encryptedData)
	if err != nil {
		return fmt.Errorf("failed to encode data: %w", err)
	}

	// Get storage nodes
	storageNodes, err := getStorageNodes()
	if err != nil {
		return fmt.Errorf("failed to get storage nodes: %w", err)
	}

	if len(storageNodes) < len(shards) {
		return fmt.Errorf("insufficient storage nodes: need %d, have %d", len(shards), len(storageNodes))
	}

	// Upload shards to storage nodes
	var shardInfos []map[string]interface{}
	for i, shard := range shards {
		nodeAddr := storageNodes[i%len(storageNodes)]
		shardID := fmt.Sprintf("%s-%s-%d", bucketName, objectKey, i)

		shardInfo, err := uploadShard(nodeAddr, shardID, bucketName, objectKey, shard, encoder.GetShardTypeString(i), i)
		if err != nil {
			return fmt.Errorf("failed to upload shard %d: %w", i, err)
		}

		shardInfos = append(shardInfos, shardInfo)
		fmt.Printf("Uploaded shard %d/%d to %s\n", i+1, len(shards), nodeAddr)
	}

	// Calculate checksum
	hasher := sha256.New()
	hasher.Write(data)
	checksum := hex.EncodeToString(hasher.Sum(nil))

	// Create object metadata
	objectData := map[string]interface{}{
		"objectKey":     objectKey,
		"size":          len(data),
		"tier":          tier,
		"shards":        shardInfos,
		"encryptionKey": encryptionKey,
		"checksum":      checksum,
		"contentType":   "application/octet-stream",
	}

	// Register object with metadata service
	if err := makeAPIRequest("POST", "/buckets/"+bucketName+"/objects", objectData, nil); err != nil {
		return fmt.Errorf("failed to register object: %w", err)
	}

	fmt.Printf("Successfully uploaded %s to %s/%s\n", filePath, bucketName, objectKey)
	return nil
}

func downloadObject(bucketName, objectKey, outputPath string) error {
	// Get object metadata
	var objectMeta map[string]interface{}
	if err := makeAPIRequest("GET", "/buckets/"+bucketName+"/objects/"+objectKey, nil, &objectMeta); err != nil {
		return fmt.Errorf("failed to get object metadata: %w", err)
	}

	shards, ok := objectMeta["shards"].([]interface{})
	if !ok {
		return fmt.Errorf("invalid shard information")
	}

	originalSize := int(objectMeta["size"].(float64))
	encryptionKey := objectMeta["encryptionKey"].(string)

	logger.Info("Starting download",
		zap.String("bucket", bucketName),
		zap.String("key", objectKey),
		zap.Int("size", originalSize))

	// Download shards
	encoder, err := erasure.NewDefaultEncoder()
	if err != nil {
		return fmt.Errorf("failed to create encoder: %w", err)
	}

	dataShards, parityShards, totalShards := encoder.GetShardInfo()
	shardData := make([][]byte, totalShards)

	for i, shardInfo := range shards {
		shardMap := shardInfo.(map[string]interface{})
		nodeAddr := shardMap["nodeAddr"].(string)
		shardID := shardMap["shardId"].(string)

		data, err := downloadShard(nodeAddr, shardID, bucketName, objectKey)
		if err != nil {
			logger.Warn("Failed to download shard", zap.Int("index", i), zap.Error(err))
			continue
		}

		shardData[i] = data
		fmt.Printf("Downloaded shard %d/%d from %s\n", i+1, len(shards), nodeAddr)
	}

	// Check if we have enough shards
	availableShards := 0
	for _, shard := range shardData {
		if shard != nil {
			availableShards++
		}
	}

	if availableShards < dataShards {
		return fmt.Errorf("insufficient shards for reconstruction: need %d, have %d", dataShards, availableShards)
	}

	// Reconstruct data
	encryptedData, err := encoder.DecodeShards(shardData, len(shardData[0])*dataShards)
	if err != nil {
		return fmt.Errorf("failed to reconstruct data: %w", err)
	}

	// Decrypt data
	data, err := decryptData(encryptedData, encryptionKey)
	if err != nil {
		return fmt.Errorf("failed to decrypt data: %w", err)
	}

	// Trim to original size
	if len(data) > originalSize {
		data = data[:originalSize]
	}

	// Write to output file
	if err := os.WriteFile(outputPath, data, 0644); err != nil {
		return fmt.Errorf("failed to write output file: %w", err)
	}

	fmt.Printf("Successfully downloaded %s/%s to %s\n", bucketName, objectKey, outputPath)
	return nil
}

func deleteObject(bucketName, objectKey string) error {
	return makeAPIRequest("DELETE", "/buckets/"+bucketName+"/objects/"+objectKey, nil, nil)
}

func listObjects(bucketName string) error {
	var objects []map[string]interface{}
	if err := makeAPIRequest("GET", "/buckets/"+bucketName+"/objects", nil, &objects); err != nil {
		return err
	}

	fmt.Printf("%-30s %-10s %-10s %-20s %-20s\n", "NAME", "SIZE", "TIER", "CREATED", "LAST ACCESSED")
	fmt.Println(strings.Repeat("-", 100))

	for _, object := range objects {
		name := object["objectKey"].(string)
		size := int64(object["size"].(float64))
		tier := object["tier"].(string)
		createdAt := object["createdAt"].(string)
		lastAccessed := object["lastAccessed"].(string)

		fmt.Printf("%-30s %-10s %-10s %-20s %-20s\n",
			name, formatBytes(size), tier, createdAt, lastAccessed)
	}

	return nil
}

func migrateTier(bucketName, objectKey, newTier string) error {
	updateData := map[string]interface{}{
		"tier": newTier,
	}

	return makeAPIRequest("PATCH", "/buckets/"+bucketName+"/objects/"+objectKey, updateData, nil)
}

func makeAPIRequest(method, path string, data interface{}, result interface{}) error {
	var body io.Reader
	if data != nil {
		jsonData, err := json.Marshal(data)
		if err != nil {
			return fmt.Errorf("failed to marshal data: %w", err)
		}
		body = bytes.NewBuffer(jsonData)
	}

	req, err := http.NewRequest(method, apiURL+path, body)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	if data != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	// Add auth token if available
	if token := viper.GetString("auth-token"); token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return fmt.Errorf("request failed with status: %d", resp.StatusCode)
	}

	if result != nil {
		if err := json.NewDecoder(resp.Body).Decode(result); err != nil {
			return fmt.Errorf("failed to decode response: %w", err)
		}
	}

	return nil
}

func getEncryptionKey(bucketName, objectKey string) (string, error) {
	// In a real implementation, this would get a data encryption key from Vault
	// For now, we'll generate a simple key
	key := make([]byte, 32)
	if _, err := rand.Read(key); err != nil {
		return "", err
	}
	return hex.EncodeToString(key), nil
}

func encryptData(data []byte, keyHex string) ([]byte, error) {
	key, err := hex.DecodeString(keyHex)
	if err != nil {
		return nil, err
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}

	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, err
	}

	ciphertext := gcm.Seal(nonce, nonce, data, nil)
	return ciphertext, nil
}

func decryptData(encryptedData []byte, keyHex string) ([]byte, error) {
	key, err := hex.DecodeString(keyHex)
	if err != nil {
		return nil, err
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}

	nonceSize := gcm.NonceSize()
	if len(encryptedData) < nonceSize {
		return nil, fmt.Errorf("ciphertext too short")
	}

	nonce, ciphertext := encryptedData[:nonceSize], encryptedData[nonceSize:]
	return gcm.Open(nil, nonce, ciphertext, nil)
}

func getStorageNodes() ([]string, error) {
	// In a real implementation, this would query the metadata service for available storage nodes
	return []string{
		"storage-node-0:8080",
		"storage-node-1:8081",
		"storage-node-2:8082",
	}, nil
}

func uploadShard(nodeAddr, shardID, bucketName, objectKey string, shardData []byte, shardType string, index int) (map[string]interface{}, error) {
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	// Add form fields
	writer.WriteField("shardId", shardID)
	writer.WriteField("bucketName", bucketName)
	writer.WriteField("objectKey", objectKey)
	writer.WriteField("shardType", shardType)
	writer.WriteField("index", strconv.Itoa(index))
	writer.WriteField("totalShards", "9")

	// Add file
	part, err := writer.CreateFormFile("shard", shardID+".shard")
	if err != nil {
		return nil, err
	}
	part.Write(shardData)

	writer.Close()

	// Make request
	resp, err := http.Post("http://"+nodeAddr+"/shard/upload", writer.FormDataContentType(), &buf)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		return nil, fmt.Errorf("upload failed with status: %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"shardId":   shardID,
		"nodeId":    nodeAddr,
		"nodeAddr":  nodeAddr,
		"shardType": shardType,
		"index":     index,
		"size":      len(shardData),
		"checksum":  result["checksum"],
	}, nil
}

func downloadShard(nodeAddr, shardID, bucketName, objectKey string) ([]byte, error) {
	url := fmt.Sprintf("http://%s/shard/download/%s?bucket=%s&object=%s", nodeAddr, shardID, bucketName, objectKey)

	resp, err := http.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("download failed with status: %d", resp.StatusCode)
	}

	return io.ReadAll(resp.Body)
}

func formatBytes(bytes int64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}