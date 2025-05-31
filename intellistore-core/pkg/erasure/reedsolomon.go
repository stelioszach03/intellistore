package erasure

import (
	"fmt"
	"io"

	"github.com/klauspost/reedsolomon"
)

const (
	// DefaultDataShards is the default number of data shards
	DefaultDataShards = 6
	// DefaultParityShards is the default number of parity shards
	DefaultParityShards = 3
	// DefaultShardSize is the default size of each shard (1MB)
	DefaultShardSize = 1024 * 1024
)

// Encoder handles Reed-Solomon encoding and decoding
type Encoder struct {
	dataShards   int
	parityShards int
	shardSize    int
	encoder      reedsolomon.Encoder
}

// NewEncoder creates a new Reed-Solomon encoder
func NewEncoder(dataShards, parityShards, shardSize int) (*Encoder, error) {
	if dataShards <= 0 || parityShards <= 0 {
		return nil, fmt.Errorf("invalid shard configuration: data=%d, parity=%d", dataShards, parityShards)
	}

	encoder, err := reedsolomon.New(dataShards, parityShards)
	if err != nil {
		return nil, fmt.Errorf("failed to create Reed-Solomon encoder: %w", err)
	}

	return &Encoder{
		dataShards:   dataShards,
		parityShards: parityShards,
		shardSize:    shardSize,
		encoder:      encoder,
	}, nil
}

// NewDefaultEncoder creates an encoder with default settings
func NewDefaultEncoder() (*Encoder, error) {
	return NewEncoder(DefaultDataShards, DefaultParityShards, DefaultShardSize)
}

// EncodeData encodes data into shards
func (e *Encoder) EncodeData(data []byte) ([][]byte, error) {
	if len(data) == 0 {
		return nil, fmt.Errorf("empty data")
	}

	// Calculate the size needed for each data shard
	shardSize := (len(data) + e.dataShards - 1) / e.dataShards

	// Create shards slice
	shards := make([][]byte, e.dataShards+e.parityShards)

	// Fill data shards
	for i := 0; i < e.dataShards; i++ {
		shards[i] = make([]byte, shardSize)
		start := i * shardSize
		end := start + shardSize
		if end > len(data) {
			end = len(data)
		}
		if start < len(data) {
			copy(shards[i], data[start:end])
		}
	}

	// Create parity shards
	for i := e.dataShards; i < e.dataShards+e.parityShards; i++ {
		shards[i] = make([]byte, shardSize)
	}

	// Encode
	if err := e.encoder.Encode(shards); err != nil {
		return nil, fmt.Errorf("failed to encode shards: %w", err)
	}

	return shards, nil
}

// DecodeShards reconstructs data from available shards
func (e *Encoder) DecodeShards(shards [][]byte, originalSize int) ([]byte, error) {
	if len(shards) != e.dataShards+e.parityShards {
		return nil, fmt.Errorf("invalid number of shards: expected %d, got %d",
			e.dataShards+e.parityShards, len(shards))
	}

	// Check if we have enough shards to reconstruct
	availableShards := 0
	for _, shard := range shards {
		if shard != nil {
			availableShards++
		}
	}

	if availableShards < e.dataShards {
		return nil, fmt.Errorf("insufficient shards for reconstruction: need %d, have %d",
			e.dataShards, availableShards)
	}

	// Reconstruct missing shards
	if err := e.encoder.Reconstruct(shards); err != nil {
		return nil, fmt.Errorf("failed to reconstruct shards: %w", err)
	}

	// Verify the reconstruction
	if ok, err := e.encoder.Verify(shards); err != nil {
		return nil, fmt.Errorf("failed to verify shards: %w", err)
	} else if !ok {
		return nil, fmt.Errorf("shard verification failed")
	}

	// Combine data shards to reconstruct original data
	data := make([]byte, 0, originalSize)
	for i := 0; i < e.dataShards; i++ {
		data = append(data, shards[i]...)
	}

	// Trim to original size
	if len(data) > originalSize {
		data = data[:originalSize]
	}

	return data, nil
}

// EncodeStream encodes data from a reader into shards
func (e *Encoder) EncodeStream(reader io.Reader) ([][]byte, int, error) {
	// Read all data first (in a real implementation, you might want to stream this)
	data, err := io.ReadAll(reader)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to read data: %w", err)
	}

	shards, err := e.EncodeData(data)
	if err != nil {
		return nil, 0, err
	}

	return shards, len(data), nil
}

// DecodeToWriter reconstructs data and writes it to a writer
func (e *Encoder) DecodeToWriter(shards [][]byte, originalSize int, writer io.Writer) error {
	data, err := e.DecodeShards(shards, originalSize)
	if err != nil {
		return err
	}

	_, err = writer.Write(data)
	return err
}

// GetShardInfo returns information about the encoding configuration
func (e *Encoder) GetShardInfo() (dataShards, parityShards, totalShards int) {
	return e.dataShards, e.parityShards, e.dataShards + e.parityShards
}

// CanReconstructWith checks if reconstruction is possible with the given number of available shards
func (e *Encoder) CanReconstructWith(availableShards int) bool {
	return availableShards >= e.dataShards
}

// MinimumShards returns the minimum number of shards needed for reconstruction
func (e *Encoder) MinimumShards() int {
	return e.dataShards
}

// MaximumFailures returns the maximum number of shard failures that can be tolerated
func (e *Encoder) MaximumFailures() int {
	return e.parityShards
}

// ShardType represents the type of a shard
type ShardType int

const (
	DataShard ShardType = iota
	ParityShard
)

// GetShardType returns the type of shard for the given index
func (e *Encoder) GetShardType(index int) ShardType {
	if index < e.dataShards {
		return DataShard
	}
	return ParityShard
}

// GetShardTypeString returns the string representation of the shard type
func (e *Encoder) GetShardTypeString(index int) string {
	if e.GetShardType(index) == DataShard {
		return "data"
	}
	return "parity"
}